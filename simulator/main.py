import json
import os
import random
import threading
import time
from datetime import datetime, timezone

import requests


def log_event(event: str, **kwargs) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "component": "simulator",
        "event": event,
    }
    payload.update(kwargs)
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")), flush=True)


def read_float(name: str, default: float, min_value: float = 0.0) -> float:
    raw = os.environ.get(name, str(default))
    try:
        val = float(raw)
    except ValueError:
        log_event("invalid_env", name=name, raw=raw, fallback=default)
        return default
    if val < min_value:
        log_event("invalid_env", name=name, raw=raw, fallback=default)
        return default
    return val


def read_int(name: str, default: int, min_value: int = 1) -> int:
    raw = os.environ.get(name, str(default))
    try:
        val = int(raw)
    except ValueError:
        log_event("invalid_env", name=name, raw=raw, fallback=default)
        return default
    if val < min_value:
        log_event("invalid_env", name=name, raw=raw, fallback=default)
        return default
    return val


def rand_wait(min_sec: float, max_sec: float) -> float:
    return random.uniform(min_sec, max_sec)


def actor_name() -> str:
    pool = [
        "alexey",
        "elena",
        "maxim",
        "olga",
        "qa-bot",
        "devops",
        "support",
    ]
    return random.choice(pool)


def maybe_sleep_with_log(min_sec: float, max_sec: float, reason: str) -> None:
    seconds = rand_wait(min_sec, max_sec)
    log_event("wait", reason=reason, seconds=round(seconds, 2))
    time.sleep(seconds)


def create_task(session: requests.Session, base_url: str, title: str, actor: str) -> dict:
    response = session.post(
        f"{base_url}/tasks",
        json={"title": title},
        headers={"X-Simulated-Actor": actor},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    log_event("task_created", actor=actor, task_id=payload.get("id"), title=payload.get("title"))
    return payload


def update_status(
    session: requests.Session, base_url: str, task_id: int, status: str, actor: str
) -> dict:
    response = session.patch(
        f"{base_url}/tasks/{task_id}/status",
        json={"status": status},
        headers={"X-Simulated-Actor": actor},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    log_event(
        "task_status_updated",
        actor=actor,
        task_id=payload.get("id"),
        new_status=payload.get("status"),
    )
    return payload


def delete_task(session: requests.Session, base_url: str, task_id: int, actor: str) -> None:
    response = session.delete(
        f"{base_url}/tasks/{task_id}",
        headers={"X-Simulated-Actor": actor},
        timeout=10,
    )
    if response.status_code not in (204, 404):
        response.raise_for_status()


def list_recent_tasks(
    session: requests.Session, base_url: str, limit: int = 100, offset: int = 0
) -> list[dict]:
    response = session.get(
        f"{base_url}/tasks",
        params={"limit": limit, "offset": offset},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        return []
    return payload


def cleanup_old_tasks(session: requests.Session, base_url: str, max_tasks: int) -> None:
    tasks: list[dict] = []
    page_size = 100
    offset = 0
    target = max(max_tasks * 2, page_size)

    while len(tasks) < target:
        page = list_recent_tasks(session, base_url, limit=page_size, offset=offset)
        if not page:
            break
        tasks.extend(page)
        if len(page) < page_size:
            break
        offset += page_size

    if len(tasks) <= max_tasks:
        return

    # API returns newest first; reverse to process oldest first.
    oldest_first = list(reversed(tasks))
    removable = [t for t in oldest_first if t.get("status") in {"done", "failed"}]
    if len(tasks) - len(removable) > max_tasks:
        removable.extend([t for t in oldest_first if t.get("status") not in {"done", "failed"}])

    to_delete_count = len(tasks) - max_tasks
    if to_delete_count <= 0:
        return

    actor = actor_name()
    deleted = 0
    for task in removable:
        if deleted >= to_delete_count:
            break
        task_id = task.get("id")
        if not isinstance(task_id, int):
            continue
        try:
            delete_task(session, base_url, task_id, actor)
            deleted += 1
        except Exception as exc:
            log_event("cleanup_error", task_id=task_id, error=str(exc))

    if deleted:
        log_event("cleanup_done", deleted=deleted, max_tasks=max_tasks)


def main() -> None:
    enabled = os.environ.get("SIMULATOR_ENABLED", "1") == "1"
    if not enabled:
        log_event("disabled")
        while True:
            time.sleep(60)

    base_url = os.environ.get("SIMULATOR_API_BASE_URL", "http://api:8000").rstrip("/")
    prefix = os.environ.get("SIMULATOR_TASK_TITLE_PREFIX", "Live Task")

    create_min = read_float("SIMULATOR_CREATE_MIN_DELAY_SECONDS", 15.0, 0.1)
    create_max = read_float("SIMULATOR_CREATE_MAX_DELAY_SECONDS", 30.0, create_min)
    stage_min = read_float("SIMULATOR_STAGE_MIN_DELAY_SECONDS", 15.0, 0.1)
    stage_max = read_float("SIMULATOR_STAGE_MAX_DELAY_SECONDS", 30.0, stage_min)
    fail_rate = read_float("SIMULATOR_FAIL_RATE", 0.2, 0.0)
    fail_tag_rate = read_float("SIMULATOR_FAIL_TAG_RATE", 0.35, 0.0)
    burst = read_int("SIMULATOR_BURST_SIZE", 3, 1)
    max_tasks = read_int("SIMULATOR_MAX_TASKS", 120, 20)
    cleanup_interval = read_float("SIMULATOR_CLEANUP_INTERVAL_SECONDS", 30.0, 5.0)
    last_cleanup_ts = 0.0

    session = requests.Session()

    log_event(
        "started",
        base_url=base_url,
        create_min=create_min,
        create_max=create_max,
        stage_min=stage_min,
        stage_max=stage_max,
        fail_rate=fail_rate,
        fail_tag_rate=fail_tag_rate,
        burst=burst,
        max_tasks=max_tasks,
        cleanup_interval=cleanup_interval,
    )

    def task_lifecycle(actor: str, task_id: int, title: str, tagged_fail: bool) -> None:
        try:
            maybe_sleep_with_log(stage_min, stage_max, "before_in_progress")
            update_status(session, base_url, task_id, "in_progress", actor)

            maybe_sleep_with_log(stage_min, stage_max, "before_final_status")
            # Tagged [FAIL] tasks fail more often to keep demos visually rich.
            effective_fail_rate = max(fail_rate, 0.7) if tagged_fail else fail_rate
            final_status = "failed" if random.random() < effective_fail_rate else "done"
            update_status(session, base_url, task_id, final_status, actor)
        except Exception as exc:
            log_event(
                "simulator_error",
                error=str(exc),
                actor=actor,
                title=title,
                task_id=task_id,
            )

    idx = 0
    while True:
        maybe_sleep_with_log(create_min, create_max, "before_create")
        for _ in range(burst):
            idx += 1
            actor = actor_name()
            tagged_fail = random.random() < fail_tag_rate
            fail_suffix = " [FAIL]" if tagged_fail else ""
            title = f"{prefix} #{idx}{fail_suffix}"
            try:
                task = create_task(session, base_url, title, actor)
                task_id = int(task["id"])
                threading.Thread(
                    target=task_lifecycle,
                    args=(actor, task_id, title, tagged_fail),
                    daemon=True,
                ).start()
            except Exception as exc:
                log_event("simulator_error", error=str(exc), actor=actor, title=title)
                time.sleep(5)

        now = time.time()
        if now - last_cleanup_ts >= cleanup_interval:
            try:
                cleanup_old_tasks(session, base_url, max_tasks=max_tasks)
            except Exception as exc:
                log_event("cleanup_error", error=str(exc))
            last_cleanup_ts = now


if __name__ == "__main__":
    main()
