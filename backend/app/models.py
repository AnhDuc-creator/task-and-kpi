"""Bảng dữ liệu. `current_value` của KPI không được lưu ở đây —
nó luôn là SUM(kpi_progress_entries.delta_value) tính khi đọc.
"""

import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"


class ExtractionStatus(str, enum.Enum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    FAILED = "failed"


class SuggestionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Kpi(Base):
    __tablename__ = "kpis"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    target_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(50))
    owner_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    owner: Mapped[Employee] = relationship()
    progress_entries: Mapped[list["KpiProgressEntry"]] = relationship(
        back_populates="kpi"
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    kpi_id: Mapped[int] = mapped_column(ForeignKey("kpis.id"))
    assignee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False), default=TaskStatus.TODO
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    kpi: Mapped[Kpi] = relationship()
    assignee: Mapped[Employee] = relationship()


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"
    __table_args__ = (
        UniqueConstraint("employee_id", "week_start", name="uq_report_employee_week"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    week_start: Mapped[date] = mapped_column(Date)
    raw_text: Mapped[str] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus, native_enum=False), default=ExtractionStatus.PENDING
    )
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee: Mapped[Employee] = relationship()
    kpi_suggestions: Mapped[list["KpiUpdateSuggestion"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    task_suggestions: Mapped[list["TaskCompletionSuggestion"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    blockers: Mapped[list["Blocker"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class KpiUpdateSuggestion(Base):
    __tablename__ = "kpi_update_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("weekly_reports.id"))
    suggested_kpi_id: Mapped[int | None] = mapped_column(
        ForeignKey("kpis.id"), nullable=True
    )
    suggested_delta: Mapped[float] = mapped_column(Float)
    evidence: Mapped[str] = mapped_column(Text)
    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus, native_enum=False), default=SuggestionStatus.PENDING
    )
    final_kpi_id: Mapped[int | None] = mapped_column(
        ForeignKey("kpis.id"), nullable=True
    )
    final_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    report: Mapped[WeeklyReport] = relationship(back_populates="kpi_suggestions")


class TaskCompletionSuggestion(Base):
    __tablename__ = "task_completion_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("weekly_reports.id"))
    suggested_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True
    )
    raw_text: Mapped[str] = mapped_column(Text)
    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus, native_enum=False), default=SuggestionStatus.PENDING
    )
    final_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    report: Mapped[WeeklyReport] = relationship(back_populates="task_suggestions")


class Blocker(Base):
    __tablename__ = "blockers"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("weekly_reports.id"))
    description: Mapped[str] = mapped_column(Text)
    related_kpi_id: Mapped[int | None] = mapped_column(
        ForeignKey("kpis.id"), nullable=True
    )

    report: Mapped[WeeklyReport] = relationship(back_populates="blockers")


class KpiProgressEntry(Base):
    __tablename__ = "kpi_progress_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    kpi_id: Mapped[int] = mapped_column(ForeignKey("kpis.id"))
    delta_value: Mapped[float] = mapped_column(Float)
    source_suggestion_id: Mapped[int | None] = mapped_column(
        ForeignKey("kpi_update_suggestions.id"), nullable=True
    )
    effective_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    kpi: Mapped[Kpi] = relationship(back_populates="progress_entries")
