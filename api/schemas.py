from typing import Literal

from pydantic import BaseModel, constr

try:
    from .models import TaskStatus
except ImportError:
    from models import TaskStatus


class TaskCreate(BaseModel):
    title: constr(strip_whitespace=True, min_length=1, max_length=255)


class TaskRead(BaseModel):
    id: int
    title: str
    status: str

    class Config:
        orm_mode = True


class TaskStatusUpdate(BaseModel):
    status: Literal[
        TaskStatus.PENDING,
        TaskStatus.IN_PROGRESS,
        TaskStatus.DONE,
        TaskStatus.FAILED,
    ]
