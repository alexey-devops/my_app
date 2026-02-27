import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from worker import main as worker_main  # noqa: E402


@pytest.fixture(autouse=True)
def clear_engine_cache():
    worker_main.reset_engine_cache()
    yield
    worker_main.reset_engine_cache()


def test_get_database_url_from_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "worker")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_DB", "tasks")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

    url = worker_main.get_database_url()

    assert url == "postgresql://worker:pass@db:5432/tasks"


def test_get_database_url_raises_without_password(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    with pytest.raises(RuntimeError):
        worker_main.get_database_url()


def test_mask_database_url():
    masked = worker_main.mask_database_url("postgresql://alice:super-secret@db:5432/tasks")

    assert masked == "postgresql://alice:***@db:5432/tasks"


def test_get_database_url_from_database_url_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./worker-local.db")
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    assert worker_main.get_database_url() == "sqlite:///./worker-local.db"


def test_get_database_url_prefers_secret_over_database_url(tmp_path, monkeypatch):
    secret_file = tmp_path / "worker-secret.txt"
    secret_file.write_text("secret", encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", "sqlite:///./worker-local.db")
    monkeypatch.setenv("POSTGRES_USER", "worker")
    monkeypatch.setenv("POSTGRES_DB", "tasks")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(secret_file))
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    url = worker_main.get_database_url()
    assert url == "postgresql://worker:secret@db:5432/tasks"


def test_process_pending_tasks_once(tmp_path, monkeypatch):
    db_file = tmp_path / "worker_tasks.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT)"
    )
    conn.execute("INSERT INTO tasks (title, status) VALUES ('task 1', 'pending')")
    conn.execute("INSERT INTO tasks (title, status) VALUES ('task 2', 'pending')")
    conn.commit()
    conn.close()

    processed_count = worker_main.process_pending_tasks_once(processing_delay_seconds=0)
    assert processed_count == 2

    conn = sqlite3.connect(db_file)
    statuses = conn.execute("SELECT status FROM tasks ORDER BY id").fetchall()
    conn.close()
    assert statuses == [("done",), ("done",)]


def test_run_worker_loop_with_single_iteration(monkeypatch):
    monkeypatch.setattr(worker_main, "process_pending_tasks_once", lambda limit=10: 0)
    worker_main.run_worker_loop(sleep_seconds=0, iterations=1)
