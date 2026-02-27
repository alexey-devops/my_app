import os
from functools import lru_cache
from typing import Generator
from urllib.parse import quote_plus

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, constr
from sqlalchemy import Column, DateTime, Integer, String, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

app = FastAPI()
Base = declarative_base()


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TaskCreate(BaseModel):
    title: constr(strip_whitespace=True, min_length=1)


class TaskRead(BaseModel):
    id: int
    title: str
    status: str

    class Config:
        orm_mode = True


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
    if direct_database_url:
        return direct_database_url

    user = os.environ.get("POSTGRES_USER", "user")
    db_name = os.environ.get("POSTGRES_DB", "tasks_db")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    password = _read_postgres_password()
    safe_password = quote_plus(password)

    return f"postgresql://{user}:{safe_password}@{host}:{port}/{db_name}"


def _mask_database_url(db_url: str) -> str:
    if "://" not in db_url or "@" not in db_url:
        return db_url
    scheme, remainder = db_url.split("://", 1)
    credentials, host_part = remainder.split("@", 1)
    if ":" in credentials:
        username, _ = credentials.split(":", 1)
        return f"{scheme}://{username}:***@{host_part}"
    return db_url


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


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def get_db() -> Generator[Session, None, None]:
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    db = session_local()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
async def read_root():
    db_url = get_database_url()
    masked_db_url = _mask_database_url(db_url)
    return HTMLResponse(
        f"<h1>Welcome to the API!</h1><p>DB URL (example): {masked_db_url}</p>"
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(title=payload.title, status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=list[TaskRead])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.id.desc()).all()


@app.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
