import os
import time
from functools import lru_cache
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


def process_pending_tasks_once(limit: int = 10) -> int:
    query_select = text(
        "SELECT id, title FROM tasks WHERE status = 'pending' ORDER BY id ASC LIMIT :limit"
    )
    query_update = text(
        "UPDATE tasks SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = :task_id"
    )

    try:
        with get_engine().begin() as conn:
            rows = conn.execute(query_select, {"limit": limit}).fetchall()
            for row in rows:
                print(f"Processing task id={row.id} title={row.title}")
                conn.execute(query_update, {"task_id": row.id})
            return len(rows)
    except SQLAlchemyError as exc:
        print(f"Failed to process tasks: {exc}")
        return 0


def run_worker_loop(sleep_seconds: int = 5, iterations: int | None = None) -> None:
    counter = 0
    while True:
        processed_count = process_pending_tasks_once()
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
