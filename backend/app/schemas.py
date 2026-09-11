"""Pydantic model cho HTTP API. Tách khỏi schema của tầng LLM."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import ExtractionStatus, SuggestionStatus, TaskStatus


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


class ReportCreate(BaseModel):
    employee_id: int
    week_start: date
    raw_text: str = Field(min_length=1)


class KpiSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    suggested_kpi_id: int | None
    suggested_delta: float
    evidence: str
    status: SuggestionStatus
    final_kpi_id: int | None
    final_delta: float | None
    review_note: str | None


class TaskSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    suggested_task_id: int | None
    raw_text: str
    status: SuggestionStatus
    final_task_id: int | None


class BlockerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: int
    description: str
    related_kpi_id: int | None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    week_start: date
    raw_text: str
    extraction_status: ExtractionStatus
    extraction_error: str | None
    provider_name: str | None
    kpi_suggestions: list[KpiSuggestionOut]
    task_suggestions: list[TaskSuggestionOut]
    blockers: list[BlockerOut]


class SuggestionContextOut(BaseModel):
    """Suggestion kèm ngữ cảnh để trang duyệt không phải gọi thêm API."""

    id: int
    report_id: int
    employee_name: str
    week_start: date
    suggested_kpi_id: int | None = None
    suggested_delta: float | None = None
    suggested_task_id: int | None = None
    raw_text: str | None = None
    evidence: str | None = None


class SuggestionQueueOut(BaseModel):
    kpi_updates: list[SuggestionContextOut]
    task_completions: list[SuggestionContextOut]


class KpiApproveIn(BaseModel):
    final_kpi_id: int
    final_delta: float
    note: str | None = None


class TaskApproveIn(BaseModel):
    final_task_id: int
