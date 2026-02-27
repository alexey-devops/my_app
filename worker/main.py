import json
import os
import random
import time
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def _read_postgres_password() -> str:
    password_file_path = os.environ.get("POSTGRES_PASSWORD_FILE")
    if password_file_path and os.path.exists(password_file_path):
        with open(password_file_path, "r", encoding="utf-8") as f:
            password = f.read().strip()
            if password:
                return password

    password = os.environ.get("POSTGRES_PASSWORD")
    if password:
        return password

    raise RuntimeError(
        "PostgreSQL password is not configured. Set POSTGRES_PASSWORD or POSTGRES_PASSWORD_FILE."
    )


def get_database_url() -> str:
    direct_database_url = os.environ.get("DATABASE_URL")
    if direct_database_url and not os.environ.get("POSTGRES_PASSWORD_FILE"):
        return direct_database_url

    user = os.environ.get("POSTGRES_USER", "user")
    db_name = os.environ.get("POSTGRES_DB", "tasks_db")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    password = _read_postgres_password()
    safe_password = quote_plus(password)

    return f"postgresql://{user}:{safe_password}@{host}:{port}/{db_name}"


@lru_cache(maxsize=1)
def get_engine():
    database_url = get_database_url()
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url, connect_args={"check_same_thread": False}, pool_pre_ping=True
        )
    return create_engine(database_url, pool_pre_ping=True)


def reset_engine_cache() -> None:
    get_engine.cache_clear()


TASK_TRANSITIONS_TOTAL = Counter(
    "task_lifecycle_transitions_total",
    "Task lifecycle transitions performed by worker or system.",
    ["from_status", "to_status", "source", "result"],
)
TASK_PROCESSING_SECONDS = Histogram(
    "task_lifecycle_processing_seconds",
    "Processing duration for task lifecycle finalization.",
    buckets=(0.5, 1, 2, 3, 5, 8, 13, 21, 34),
)
TASK_STATUS_COUNT = Gauge(
    "task_lifecycle_status_count",
    "Current number of tasks by status from worker DB polling.",
    ["status"],
)
KNOWN_STATUSES = ["pending", "in_progress", "done", "failed"]


def log_event(event: str, **kwargs) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "component": "worker",
        "event": event,
    }
    payload.update(kwargs)
    print(json.dumps(payload, ensure_ascii=True), flush=True)


def _read_float_env(
    name: str,
    default: float,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default

    try:
        parsed = float(raw_value)
    except ValueError:
        log_event(
            "worker_invalid_env",
            name=name,
            raw_value=raw_value,
            fallback=default,
        )
        return default

    if min_value is not None and parsed < min_value:
        log_event(
            "worker_invalid_env",
            name=name,
            raw_value=raw_value,
            fallback=default,
        )
        return default
    if max_value is not None and parsed > max_value:
        log_event(
            "worker_invalid_env",
            name=name,
            raw_value=raw_value,
            fallback=default,
        )
        return default
    return parsed


def _read_int_env(name: str, default: int, min_value: int = 1) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default

    try:
        parsed = int(raw_value)
    except ValueError:
        log_event(
            "worker_invalid_env",
            name=name,
            raw_value=raw_value,
            fallback=default,
        )
        return default

    if parsed < min_value:
        log_event(
            "worker_invalid_env",
            name=name,
            raw_value=raw_value,
            fallback=default,
        )
        return default
    return parsed


def refresh_status_metrics() -> None:
    query = text("SELECT status, COUNT(*) AS c FROM tasks GROUP BY status")
    counts = {status: 0 for status in KNOWN_STATUSES}
    try:
        with get_engine().connect() as conn:
            rows = conn.execute(query).fetchall()
            for row in rows:
                if row.status in counts:
                    counts[row.status] = int(row.c)
    except SQLAlchemyError:
        return

    for status_name, value in counts.items():
        TASK_STATUS_COUNT.labels(status=status_name).set(value)


def mask_database_url(db_url: str) -> str:
    if "://" not in db_url or "@" not in db_url:
        return db_url
    scheme, remainder = db_url.split("://", 1)
    credentials, host_part = remainder.split("@", 1)
    if ":" in credentials:
        username, _ = credentials.split(":", 1)
        return f"{scheme}://{username}:***@{host_part}"
    return db_url


def should_fail_task(task_title: str) -> bool:
    # Deterministic way to demonstrate failure path in demos.
    if "[fail]" in task_title.lower():
        return True

    # Optional probabilistic failures to emulate flaky external systems.
    failure_rate = _read_float_env("WORKER_FAILURE_RATE", default=0.0, min_value=0.0, max_value=1.0)
    if failure_rate == 0:
        return False
    return random.random() < failure_rate


def process_pending_tasks_once(limit: int = 10, processing_delay_seconds: Optional[float] = None) -> int:
    if processing_delay_seconds is None:
        processing_delay_seconds = _read_float_env(
            "WORKER_PROCESSING_DELAY_SECONDS",
            default=3.0,
            min_value=0.0,
        )

    query_select = text(
        "SELECT id, title FROM tasks WHERE status = 'pending' ORDER BY id ASC LIMIT :limit"
    )
    query_mark_in_progress = text(
        "UPDATE tasks SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP "
        "WHERE id = :task_id AND status = 'pending'"
    )
    query_mark_done = text(
        "UPDATE tasks SET status = 'done', updated_at = CURRENT_TIMESTAMP "
        "WHERE id = :task_id AND status = 'in_progress'"
    )
    query_mark_failed = text(
        "UPDATE tasks SET status = 'failed', updated_at = CURRENT_TIMESTAMP "
        "WHERE id = :task_id AND status = 'in_progress'"
    )

    try:
        with get_engine().connect() as conn:
            rows = conn.execute(query_select, {"limit": limit}).fetchall()

        processed_count = 0
        for row in rows:
            with get_engine().begin() as conn:
                reserved = conn.execute(query_mark_in_progress, {"task_id": row.id})
                if reserved.rowcount != 1:
                    continue

            TASK_TRANSITIONS_TOTAL.labels(
                from_status="pending",
                to_status="in_progress",
                source="worker",
                result="success",
            ).inc()
            log_event(
                "task_transition",
                task_id=row.id,
                title=row.title,
                from_status="pending",
                to_status="in_progress",
                source="worker",
                processing_delay_seconds=processing_delay_seconds,
            )
            refresh_status_metrics()

            started_at = time.monotonic()
            time.sleep(processing_delay_seconds)

            try:
                if should_fail_task(row.title):
                    raise RuntimeError("Task marked to fail")
                with get_engine().begin() as conn:
                    updated = conn.execute(query_mark_done, {"task_id": row.id})
                    if updated.rowcount != 1:
                        continue
                TASK_TRANSITIONS_TOTAL.labels(
                    from_status="in_progress",
                    to_status="done",
                    source="worker",
                    result="success",
                ).inc()
                TASK_PROCESSING_SECONDS.observe(time.monotonic() - started_at)
                log_event(
                    "task_transition",
                    task_id=row.id,
                    title=row.title,
                    from_status="in_progress",
                    to_status="done",
                    source="worker",
                    result="success",
                )
            except Exception:
                with get_engine().begin() as conn:
                    updated = conn.execute(query_mark_failed, {"task_id": row.id})
                    if updated.rowcount != 1:
                        continue
                TASK_TRANSITIONS_TOTAL.labels(
                    from_status="in_progress",
                    to_status="failed",
                    source="worker",
                    result="error",
                ).inc()
                TASK_PROCESSING_SECONDS.observe(time.monotonic() - started_at)
                log_event(
                    "task_transition",
                    task_id=row.id,
                    title=row.title,
                    from_status="in_progress",
                    to_status="failed",
                    source="worker",
                    result="error",
                )
            processed_count += 1
            refresh_status_metrics()
        return processed_count
    except SQLAlchemyError as exc:
        log_event("worker_db_error", error=str(exc))
        return 0


def run_worker_loop(sleep_seconds: int = 5, iterations: int | None = None) -> None:
    batch_size = _read_int_env("WORKER_BATCH_SIZE", default=10, min_value=1)
    counter = 0
    while True:
        processed_count = process_pending_tasks_once(limit=batch_size)
        if processed_count == 0:
            print("Worker is active, no pending tasks found.", flush=True)
        else:
            print(f"Worker processed {processed_count} task(s).", flush=True)
        if iterations is not None:
            counter += 1
            if counter >= iterations:
                return
        time.sleep(sleep_seconds)


def main() -> None:
    metrics_port = int(os.environ.get("WORKER_METRICS_PORT", "9102"))
    start_http_server(metrics_port)
    refresh_status_metrics()
    log_event("worker_started", metrics_port=metrics_port)
    db_url = get_database_url()
    log_event("worker_db_ready", database_url_masked=mask_database_url(db_url))
    run_worker_loop()


if __name__ == "__main__":
    main()
