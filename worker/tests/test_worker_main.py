import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from worker import main as worker_main  # noqa: E402


def test_get_database_url_from_env(monkeypatch):
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "worker")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_DB", "tasks")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

    url = worker_main.get_database_url()

    assert url == "postgresql://worker:pass@db:5432/tasks"


def test_get_database_url_raises_without_password(monkeypatch):
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    with pytest.raises(RuntimeError):
        worker_main.get_database_url()


def test_mask_database_url():
    masked = worker_main.mask_database_url("postgresql://alice:super-secret@db:5432/tasks")

    assert masked == "postgresql://alice:***@db:5432/tasks"


def test_run_worker_loop_with_single_iteration():
    worker_main.run_worker_loop(sleep_seconds=0, iterations=1)
