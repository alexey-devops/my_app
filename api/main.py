import json
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from sqlalchemy.orm import Session
from starlette.responses import Response

try:
    from .db import (
        get_database_url,
        get_db,
        get_engine,
        reset_engine_cache,
    )
    from .models import Base, Task, TaskStatus
    from .schemas import TaskCreate, TaskRead, TaskStatusUpdate
except ImportError:
    from db import get_database_url, get_db, get_engine, reset_engine_cache
    from models import Base, Task, TaskStatus
    from schemas import TaskCreate, TaskRead, TaskStatusUpdate

app = FastAPI(title="Tasks API", version="1.0.0")

TASKS_CREATED_TOTAL = Counter(
    "task_lifecycle_api_created_total",
    "Total number of tasks created via API.",
)
TASK_STATUS_UPDATES_TOTAL = Counter(
    "task_lifecycle_api_status_update_total",
    "Task status updates triggered via API.",
    ["from_status", "to_status"],
)
TASK_STATUS_COUNT = Gauge(
    "task_lifecycle_api_status_count",
    "Current number of tasks by status from API perspective.",
    ["status"],
)
KNOWN_STATUSES = [
    TaskStatus.PENDING,
    TaskStatus.IN_PROGRESS,
    TaskStatus.DONE,
    TaskStatus.FAILED,
]


def log_event(event: str, **kwargs) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "component": "api",
        "event": event,
    }
    payload.update(kwargs)
    print(json.dumps(payload, ensure_ascii=True), flush=True)


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def refresh_status_metrics(db: Session) -> None:
    counts = {status: 0 for status in KNOWN_STATUSES}
    rows = db.query(Task.status).all()
    for (status_value,) in rows:
        if status_value in counts:
            counts[status_value] += 1
    for status_name, value in counts.items():
        TASK_STATUS_COUNT.labels(status=status_name).set(value)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    session = next(get_db())
    try:
        refresh_status_metrics(session)
    finally:
        session.close()


@app.get("/")
async def read_root():
    return {
        "service": "tasks-api",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(title=payload.title, status=TaskStatus.PENDING)
    db.add(task)
    db.commit()
    db.refresh(task)
    TASKS_CREATED_TOTAL.inc()
    refresh_status_metrics(db)
    log_event(
        "task_created",
        task_id=task.id,
        title=task.title,
        status=task.status,
    )
    return task


@app.get("/tasks", response_model=list[TaskRead])
def list_tasks(
    status_filter: Optional[
        Literal[
            TaskStatus.PENDING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.DONE,
            TaskStatus.FAILED,
        ]
    ] = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    return query.order_by(Task.id.desc()).offset(offset).limit(limit).all()


@app.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.patch("/tasks/{task_id}/status", response_model=TaskRead)
def update_task_status(task_id: int, payload: TaskStatusUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    previous_status = task.status
    task.status = payload.status
    db.commit()
    db.refresh(task)
    TASK_STATUS_UPDATES_TOTAL.labels(
        from_status=previous_status,
        to_status=task.status,
    ).inc()
    refresh_status_metrics(db)
    log_event(
        "task_status_updated",
        task_id=task.id,
        title=task.title,
        from_status=previous_status,
        to_status=task.status,
        source="api",
    )
    return task


__all__ = ["app", "init_db", "reset_engine_cache"]
