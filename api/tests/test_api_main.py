import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main  # noqa: E402


def test_get_database_url_prefers_password_file(tmp_path, monkeypatch):
    secret_file = tmp_path / "pg_pass.txt"
    secret_file.write_text("file-secret", encoding="utf-8")

    monkeypatch.setenv("POSTGRES_USER", "alice")
    monkeypatch.setenv("POSTGRES_DB", "tasks")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_PASSWORD", "env-secret")
    monkeypatch.setenv("POSTGRES_PASSWORD_FILE", str(secret_file))

    url = main.get_database_url()

    assert url == "postgresql://alice:file-secret@db:5432/tasks"


def test_get_database_url_uses_env_password(monkeypatch):
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "env-secret")

    url = main.get_database_url()

    assert "env-secret" in url


def test_get_database_url_raises_without_password(monkeypatch):
    monkeypatch.delenv("POSTGRES_PASSWORD_FILE", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    with pytest.raises(RuntimeError):
        main.get_database_url()


def test_health_endpoint(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-pass")

    client = TestClient(main.app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
