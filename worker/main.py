import os
import time
from urllib.parse import quote_plus


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
    user = os.environ.get("POSTGRES_USER", "user")
    db_name = os.environ.get("POSTGRES_DB", "tasks_db")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    password = _read_postgres_password()
    safe_password = quote_plus(password)

    return f"postgresql://{user}:{safe_password}@{host}:{port}/{db_name}"


def mask_database_url(db_url: str) -> str:
    if "://" not in db_url or "@" not in db_url:
        return db_url
    scheme, remainder = db_url.split("://", 1)
    credentials, host_part = remainder.split("@", 1)
    if ":" in credentials:
        username, _ = credentials.split(":", 1)
        return f"{scheme}://{username}:***@{host_part}"
    return db_url


def run_worker_loop(sleep_seconds: int = 5, iterations: int | None = None) -> None:
    counter = 0
    while True:
        print("Worker is active, performing dummy task...")
        if iterations is not None:
            counter += 1
            if counter >= iterations:
                return
        time.sleep(sleep_seconds)


def main() -> None:
    print("Worker started. Listening for tasks...")
    db_url = get_database_url()
    print(f"Worker using DB URL (example): {mask_database_url(db_url)}")
    run_worker_loop()


if __name__ == "__main__":
    main()
