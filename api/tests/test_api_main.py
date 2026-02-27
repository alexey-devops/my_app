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


def test_get_database_url_prefers_secret_over_database_url(tmp_path, monkeypatch):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("top-secret", encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", "sqlite:///./local.db")
    monkeypatch.setenv("POSTGRES_USER", "alice")
    monkeypatch.setenv("POSTGRES_DB", "tasks")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(secret_file))
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    url = api_main.get_database_url()
    assert url == "postgresql://alice:top-secret@db:5432/tasks"


def test_health_endpoint(tmp_path, monkeypatch):
    db_file = tmp_path / "health.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    with TestClient(api_main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_list_tasks(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    with TestClient(api_main.app) as client:
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


def test_list_tasks_with_status_filter_and_pagination(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks_filter.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    with TestClient(api_main.app) as client:
        first = client.post("/tasks", json={"title": "Task A"}).json()
        second = client.post("/tasks", json={"title": "Task B"}).json()
        third = client.post("/tasks", json={"title": "Task C"}).json()

        patch_response = client.patch(
            f"/tasks/{second['id']}/status", json={"status": "done"}
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["status"] == "done"

        done_response = client.get("/tasks", params={"status": "done"})
        assert done_response.status_code == 200
        done_tasks = done_response.json()
        assert len(done_tasks) == 1
        assert done_tasks[0]["id"] == second["id"]

        paged_response = client.get("/tasks", params={"limit": 2, "offset": 0})
        assert paged_response.status_code == 200
        paged_tasks = paged_response.json()
        assert len(paged_tasks) == 2
        assert paged_tasks[0]["id"] == third["id"]
        assert paged_tasks[1]["id"] == second["id"]


def test_create_task_rejects_blank_title(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks_invalid.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    with TestClient(api_main.app) as client:
        response = client.post("/tasks", json={"title": "   "})

    assert response.status_code == 422


def test_update_task_status_returns_404_for_unknown_id(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks_404.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    with TestClient(api_main.app) as client:
        response = client.patch("/tasks/999/status", json={"status": "done"})

    assert response.status_code == 404


def test_list_tasks_rejects_invalid_status_filter(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks_invalid_filter.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    with TestClient(api_main.app) as client:
        response = client.get("/tasks", params={"status": "unknown"})

    assert response.status_code == 422


def test_get_task_returns_404_for_unknown_id(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks_get_404.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    with TestClient(api_main.app) as client:
        response = client.get("/tasks/999")

    assert response.status_code == 404


def test_update_task_status_rejects_invalid_status(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks_invalid_status.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    with TestClient(api_main.app) as client:
        created = client.post("/tasks", json={"title": "Task for invalid status"}).json()
        response = client.patch(
            f"/tasks/{created['id']}/status", json={"status": "unknown"}
        )

    assert response.status_code == 422


def test_list_tasks_respects_offset(tmp_path, monkeypatch):
    db_file = tmp_path / "tasks_offset.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    with TestClient(api_main.app) as client:
        first = client.post("/tasks", json={"title": "First"}).json()
        second = client.post("/tasks", json={"title": "Second"}).json()
        third = client.post("/tasks", json={"title": "Third"}).json()

        response = client.get("/tasks", params={"limit": 1, "offset": 1})
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) == 1
        assert tasks[0]["id"] == second["id"]
        assert tasks[0]["id"] != third["id"]
        assert tasks[0]["id"] != first["id"]
