import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from api import main as api_main  # noqa: E402


@pytest.fixture(autouse=True)
def clear_engine_cache():
    api_main.reset_engine_cache()
    yield
    api_main.reset_engine_cache()


def test_get_database_url_prefers_password_file(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    secret_file = tmp_path / "pg_pass.txt"
    secret_file.write_text("file-secret", encoding="utf-8")

    monkeypatch.setenv("POSTGRES_USER", "alice")
    monkeypatch.setenv("POSTGRES_DB", "tasks")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_PASSWORD", "env-secret")
    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(secret_file))

    url = api_main.get_database_url()

    assert url == "postgresql://alice:file-secret@db:5432/tasks"


def test_get_database_url_uses_env_password(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "env-secret")

    url = api_main.get_database_url()

    assert "env-secret" in url


def test_get_database_url_raises_without_password(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    with pytest.raises(RuntimeError):
        api_main.get_database_url()


def test_get_database_url_from_database_url_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./local.db")
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    assert api_main.get_database_url() == "sqlite:///./local.db"


def test_health_endpoint(tmp_path, monkeypatch):
    db_file = tmp_path / "health.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    client = TestClient(api_main.app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_list_tasks(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    client = TestClient(api_main.app)

    create_response = client.post("/tasks", json={"title": "  First task  "})
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == "First task"
    assert created["status"] == "pending"
    assert "id" in created

    list_response = client.get("/tasks")
    assert list_response.status_code == 200
    tasks = list_response.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "First task"

    task_id = created["id"]
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == task_id


def test_create_task_rejects_blank_title(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks_invalid.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    client = TestClient(api_main.app)
    response = client.post("/tasks", json={"title": "   "})

    assert response.status_code == 422
