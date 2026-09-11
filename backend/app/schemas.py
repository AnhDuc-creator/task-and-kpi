"""Pydantic model cho HTTP API. Tách khỏi schema của tầng LLM."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import TaskStatus


class EmployeeCreate(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class KpiCreate(BaseModel):
    name: str = Field(min_length=1)
    target_value: float = Field(gt=0)
    unit: str = Field(min_length=1)
    owner_id: int
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def check_period(self) -> "KpiCreate":
        if self.period_end < self.period_start:
            raise ValueError("period_end phải không nhỏ hơn period_start")
        return self


class KpiUpdate(BaseModel):
    name: str | None = None
    target_value: float | None = Field(default=None, gt=0)
    unit: str | None = None
    period_start: date | None = None
    period_end: date | None = None


class KpiOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    target_value: float
    unit: str
    owner_id: int
    period_start: date
    period_end: date


class TaskCreate(BaseModel):
    title: str = Field(min_length=1)
    kpi_id: int
    assignee_id: int


class TaskUpdate(BaseModel):
    title: str | None = None
    status: TaskStatus | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    kpi_id: int
    assignee_id: int
    status: TaskStatus
    completed_at: datetime | None
