import os
import time
from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def _read_postgres_password() -> str:
    password_file_path = os.environ.get("POSTGRES_PASSWORD_FILE")
    if password_file_path and os.path.exists(password_file_path):
        with open(password_file_path, "r") as f:
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


def mask_database_url(db_url: str) -> str:
    if "://" not in db_url or "@" not in db_url:
        return db_url
    scheme, remainder = db_url.split("://", 1)
    credentials, host_part = remainder.split("@", 1)
    if ":" in credentials:
        username, _ = credentials.split(":", 1)
        return f"{scheme}://{username}:***@{host_part}"
    return db_url


def process_pending_tasks_once(limit: int = 10, processing_delay_seconds: Optional[float] = None) -> int:
    if processing_delay_seconds is None:
        processing_delay_seconds = float(os.environ.get("WORKER_PROCESSING_DELAY_SECONDS", "3"))

    query_select = text(
        "SELECT id, title FROM tasks WHERE status = 'pending' ORDER BY id ASC LIMIT :limit"
    )
    query_mark_in_progress = text(
        "UPDATE tasks SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP "
        "WHERE id = :task_id AND status = 'pending'"
    )
    query_mark_done = text(
        "UPDATE tasks SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = :task_id"
    )
    query_mark_failed = text(
        "UPDATE tasks SET status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE id = :task_id"
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

            print(
                f"Task id={row.id} moved to in_progress. "
                f"Will finish in {processing_delay_seconds} sec."
            )
            time.sleep(processing_delay_seconds)

            try:
                with get_engine().begin() as conn:
                    updated = conn.execute(query_mark_done, {"task_id": row.id})
                    if updated.rowcount != 1:
                        continue
            except Exception:
                with get_engine().begin() as conn:
                    conn.execute(query_mark_failed, {"task_id": row.id})
                continue

            processed_count += 1
        return processed_count
    except SQLAlchemyError as exc:
        print(f"Failed to process tasks: {exc}")
        return 0


def run_worker_loop(sleep_seconds: int = 5, iterations: int | None = None) -> None:
    batch_size = int(os.environ.get("WORKER_BATCH_SIZE", "10"))
    counter = 0
    while True:
        processed_count = process_pending_tasks_once(limit=batch_size)
        if processed_count == 0:
            print("Worker is active, no pending tasks found.")
        else:
            print(f"Worker processed {processed_count} task(s).")
        if iterations is not None:
            counter += 1
            if counter >= iterations:
                return
        time.sleep(sleep_seconds)


def main() -> None:
    print("Worker started. Listening for tasks...")
    db_url = get_database_url()
    print(f"Worker using DB URL: {mask_database_url(db_url)}")
    run_worker_loop()


if __name__ == "__main__":
    main()
