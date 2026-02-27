from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

try:
    from .db import (
        get_database_url,
        get_db,
        get_engine,
        mask_database_url,
        reset_engine_cache,
    )
    from .models import Base, Task, TaskStatus
    from .schemas import TaskCreate, TaskRead, TaskStatusUpdate
except ImportError:
    from db import get_database_url, get_db, get_engine, mask_database_url, reset_engine_cache
    from models import Base, Task, TaskStatus
    from schemas import TaskCreate, TaskRead, TaskStatusUpdate

app = FastAPI(title="Tasks API", version="1.0.0")


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
async def read_root():
    db_url = get_database_url()
    masked_db_url = mask_database_url(db_url)
    return HTMLResponse(
        f"<h1>Welcome to the API!</h1><p>DB URL (example): {masked_db_url}</p>"
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(title=payload.title, status=TaskStatus.PENDING)
    db.add(task)
    db.commit()
    db.refresh(task)
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

    task.status = payload.status
    db.commit()
    db.refresh(task)
    return task


__all__ = ["app", "init_db", "reset_engine_cache"]
