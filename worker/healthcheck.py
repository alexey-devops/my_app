import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

try:
    from .main import get_engine
except ImportError:
    from main import get_engine


def check_database() -> None:
    with get_engine().connect() as conn:
        conn.execute(text("SELECT 1"))


if __name__ == "__main__":
    try:
        check_database()
        print("Worker healthcheck successful", flush=True)
        sys.exit(0)
    except (SQLAlchemyError, RuntimeError, ValueError) as exc:
        print(f"Worker healthcheck failed: {exc}", flush=True)
        sys.exit(1)
