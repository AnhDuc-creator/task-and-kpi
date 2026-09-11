# Backend (Giai đoạn 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây toàn bộ backend FastAPI cho MVP "AI đọc báo cáo tuần và đề xuất cập nhật tiến độ KPI", kèm bộ test pytest chạy được không cần mạng.

**Architecture:** FastAPI + SQLAlchemy 2.0 + SQLite. `routers` chỉ dịch HTTP ↔ service; `services` giữ toàn bộ nghiệp vụ và làm chủ transaction; `rules.py` là hàm thuần tính cảnh báo rủi ro; `llm/` là tầng provider độc lập với database (nhận Pydantic vào, trả Pydantic ra). Tiến độ KPI lưu dưới dạng sổ cái chỉ-ghi-thêm `kpi_progress_entries`; `current_value` luôn được tính bằng `SUM(delta_value)` khi đọc, không có cột lưu sẵn.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (kiểu `Mapped`/`mapped_column`), Pydantic v2, pydantic-settings, anthropic SDK, pytest, httpx (cho `TestClient`).

**Spec:** `docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md`

## Global Constraints

- Tên biến, hàm, class, bảng, trường: **tiếng Anh**. Tài liệu, comment giải thích nghiệp vụ, thông điệp lỗi hướng người dùng: **tiếng Việt**.
- `LLM_PROVIDER` mặc định là `mock`. **Không test nào được gọi mạng.**
- Model Anthropic: đọc từ biến môi trường `ANTHROPIC_MODEL`, mặc định `claude-sonnet-5`. Code ứng dụng (provider, factory, router) **không** được hardcode tên model — nó chỉ xuất hiện ở giá trị mặc định trong `config.py`, trong `.env.example`, và trong test khẳng định chính giá trị mặc định đó.
- Ngưỡng cảnh báo rủi ro là hằng số có tên `RISK_THRESHOLD = 0.8`, không viết số `0.8` rải rác.
- "Hôm nay" luôn được tiêm vào hàm qua tham số `today: date`; **không** gọi `date.today()` trong `rules.py` hay trong service.
- `current_value` **không** được lưu thành cột trên bảng `kpis`.
- `validate_extraction_result` là cổng kiểm tra duy nhất áp lên output của **mọi** provider, và được gọi ở tầng service ngay sau `provider.extract(...)` — không bao giờ gọi bên trong một provider. Nó chặn id ngoài catalog và `delta_value` không hữu hạn; vi phạm → báo cáo `failed`, không tạo suggestion nào.
- Trường `suggested_*` không bao giờ bị ghi đè; sửa của quản lý đi vào `final_*`.
- Mã lỗi: `404` không tìm thấy, `409` xung đột trạng thái, `422` dữ liệu vào sai.
- MVP chỉ hỗ trợ KPI **càng cao càng tốt**. Không thêm trường `direction` hay nhánh xử lý chiều ngược lại.
- Mọi lệnh chạy từ thư mục `backend/`, trong virtualenv đã kích hoạt.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `backend/pyproject.toml` | Khai báo dependency và cấu hình pytest |
| `backend/.env.example` | Mẫu biến môi trường |
| `backend/app/config.py` | `Settings` đọc từ `.env` |
| `backend/app/db.py` | Engine, `SessionLocal`, `Base`, dependency `get_db` |
| `backend/app/errors.py` | `ConflictError`, `NotFoundError` (lỗi nghiệp vụ, không phụ thuộc HTTP) |
| `backend/app/models.py` | Toàn bộ bảng SQLAlchemy + enum |
| `backend/app/rules.py` | Luật cảnh báo rủi ro (hàm thuần) |
| `backend/app/schemas.py` | Pydantic request/response của HTTP API |
| `backend/app/llm/base.py` | Schema trích xuất, `LlmProvider`, `ExtractionError`, validate theo catalog |
| `backend/app/llm/mock.py` | `MockProvider` (mặc định) và `ScriptedProvider` (cho test) |
| `backend/app/llm/prompt.py` | Dựng system prompt và user prompt |
| `backend/app/llm/anthropic_provider.py` | Adapter Anthropic dùng structured outputs |
| `backend/app/llm/factory.py` | `get_provider(settings)` |
| `backend/app/services/extraction.py` | Nộp báo cáo, chạy trích xuất, trích lại |
| `backend/app/services/approval.py` | Duyệt / từ chối suggestion, ghi sổ cái (transactional) |
| `backend/app/services/dashboard.py` | Tính `current_value` và ghép với `rules.py` |
| `backend/app/routers/*.py` | Một router cho mỗi nhóm tài nguyên |
| `backend/app/main.py` | Khởi tạo app, gắn router, exception handler |
| `backend/tests/*` | Test theo từng tầng |

---

### Task 1: Scaffold dự án, config, database session

**Files:**
- Create: `backend/pyproject.toml`, `backend/.env.example`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/tests/__init__.py`
- Test: `backend/tests/test_config.py`, `backend/tests/test_health.py`

**Interfaces:**
- Consumes: (không có — task đầu tiên)
- Produces: `app.config.Settings` (các trường `database_url: str`, `llm_provider: str`, `anthropic_api_key: str | None`, `anthropic_model: str`), `app.config.get_settings() -> Settings`; `app.db.Base`, `app.db.SessionLocal`, `app.db.engine`, `app.db.get_db()`; `app.main.app` (FastAPI instance)

- [ ] **Step 1: Tạo `backend/pyproject.toml`**

```toml
[project]
name = "kpi-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy>=2.0",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "anthropic>=0.40",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "httpx>=0.27",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Tạo `backend/.env.example`**

```
# mock = không gọi mạng (mặc định, dùng cho test và phát triển)
# anthropic = gọi Claude thật
LLM_PROVIDER=mock
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-5
DATABASE_URL=sqlite:///./kpi.db
```

- [ ] **Step 3: Tạo virtualenv và cài dependency**

PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

- [ ] **Step 4: Viết test thất bại cho config và health check**

`backend/tests/test_config.py`:

```python
from app.config import Settings


def test_default_provider_is_mock():
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "mock"


def test_default_model_is_sonnet_5():
    settings = Settings(_env_file=None)
    assert settings.anthropic_model == "claude-sonnet-5"
```

`backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_config.py tests/test_health.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 6: Viết `backend/app/__init__.py` và `backend/tests/__init__.py`**

Cả hai là file rỗng.

- [ ] **Step 7: Viết `backend/app/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./kpi.db"
    llm_provider: str = "mock"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 8: Viết `backend/app/db.py`**

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    get_settings().database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 9: Viết `backend/app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="KPI Weekly Report API")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 10: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_config.py tests/test_health.py -v`
Expected: PASS (3 test)

- [ ] **Step 11: Commit**

```bash
git add backend/pyproject.toml backend/.env.example backend/app backend/tests
git commit -m "feat(backend): scaffold FastAPI app, settings va database session"
```

---

### Task 2: Luật cảnh báo rủi ro (`rules.py`)

Hàm thuần, không chạm database. Đây là tầng logic dễ sai nhất nên được viết trước và test dày.

**Files:**
- Create: `backend/app/rules.py`
- Test: `backend/tests/test_rules.py`

**Interfaces:**
- Consumes: (không có)
- Produces: `app.rules.RISK_THRESHOLD: float`; `app.rules.KpiStatus` (enum `str`, giá trị `on_track`/`at_risk`/`completed`); `app.rules.KpiEvaluation` (dataclass đông cứng: `actual_value: float`, `target_value: float`, `expected_value: float`, `elapsed_ratio: float`, `percent_complete: float`, `status: KpiStatus`, `at_risk: bool`); `app.rules.compute_elapsed_ratio(period_start: date, period_end: date, today: date) -> float`; `app.rules.evaluate_kpi(*, target_value: float, actual_value: float, period_start: date, period_end: date, today: date) -> KpiEvaluation`

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_rules.py`:

```python
from datetime import date

import pytest

from app.rules import KpiStatus, compute_elapsed_ratio, evaluate_kpi

START = date(2026, 1, 1)
END = date(2026, 1, 11)  # kỳ dài 10 ngày


def test_elapsed_ratio_before_period_is_zero():
    assert compute_elapsed_ratio(START, END, date(2025, 12, 20)) == 0.0


def test_elapsed_ratio_at_start_is_zero():
    assert compute_elapsed_ratio(START, END, START) == 0.0


def test_elapsed_ratio_midway():
    assert compute_elapsed_ratio(START, END, date(2026, 1, 6)) == 0.5


def test_elapsed_ratio_after_period_is_one():
    assert compute_elapsed_ratio(START, END, date(2026, 3, 1)) == 1.0


def test_elapsed_ratio_zero_length_period_is_one():
    assert compute_elapsed_ratio(START, START, START) == 1.0


def test_before_period_never_at_risk():
    result = evaluate_kpi(
        target_value=100.0,
        actual_value=0.0,
        period_start=START,
        period_end=END,
        today=date(2025, 12, 20),
    )
    assert result.expected_value == 0.0
    assert result.at_risk is False
    assert result.status is KpiStatus.ON_TRACK


def test_just_below_threshold_is_at_risk():
    # elapsed 0.5 -> expected 50 -> ngưỡng 0.8 * 50 = 40
    result = evaluate_kpi(
        target_value=100.0,
        actual_value=39.9,
        period_start=START,
        period_end=END,
        today=date(2026, 1, 6),
    )
    assert result.expected_value == 50.0
    assert result.at_risk is True
    assert result.status is KpiStatus.AT_RISK


def test_exactly_at_threshold_is_not_at_risk():
    result = evaluate_kpi(
        target_value=100.0,
        actual_value=40.0,
        period_start=START,
        period_end=END,
        today=date(2026, 1, 6),
    )
    assert result.at_risk is False
    assert result.status is KpiStatus.ON_TRACK


def test_just_above_threshold_is_not_at_risk():
    result = evaluate_kpi(
        target_value=100.0,
        actual_value=40.1,
        period_start=START,
        period_end=END,
        today=date(2026, 1, 6),
    )
    assert result.at_risk is False


def test_reaching_target_is_completed():
    result = evaluate_kpi(
        target_value=100.0,
        actual_value=100.0,
        period_start=START,
        period_end=END,
        today=date(2026, 1, 6),
    )
    assert result.status is KpiStatus.COMPLETED
    assert result.percent_complete == 1.0


def test_percent_complete_is_not_capped():
    result = evaluate_kpi(
        target_value=100.0,
        actual_value=120.0,
        period_start=START,
        period_end=END,
        today=date(2026, 1, 6),
    )
    assert result.percent_complete == 1.2


def test_after_period_expected_equals_target():
    result = evaluate_kpi(
        target_value=100.0,
        actual_value=50.0,
        period_start=START,
        period_end=END,
        today=date(2026, 3, 1),
    )
    assert result.expected_value == 100.0
    assert result.status is KpiStatus.AT_RISK


def test_non_positive_target_is_rejected():
    with pytest.raises(ValueError):
        evaluate_kpi(
            target_value=0.0,
            actual_value=0.0,
            period_start=START,
            period_end=END,
            today=date(2026, 1, 6),
        )
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_rules.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.rules'`

- [ ] **Step 3: Viết `backend/app/rules.py`**

```python
"""Luật cố định tính tiến độ kỳ vọng và cảnh báo rủi ro cho KPI.

Toàn bộ module là hàm thuần: không chạm database, không đọc đồng hồ hệ thống.
"Hôm nay" luôn được truyền vào qua tham số `today`.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum

RISK_THRESHOLD = 0.8


class KpiStatus(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    COMPLETED = "completed"


@dataclass(frozen=True)
class KpiEvaluation:
    actual_value: float
    target_value: float
    expected_value: float
    elapsed_ratio: float
    percent_complete: float
    status: KpiStatus
    at_risk: bool


def compute_elapsed_ratio(period_start: date, period_end: date, today: date) -> float:
    """Tỉ lệ thời gian đã trôi qua của kỳ, kẹp trong đoạn [0, 1].

    Kỳ dài 0 ngày được coi là đã trôi qua hoàn toàn (tránh chia cho 0).
    """
    total_days = (period_end - period_start).days
    if total_days <= 0:
        return 1.0
    elapsed_days = (today - period_start).days
    return min(max(elapsed_days / total_days, 0.0), 1.0)


def evaluate_kpi(
    *,
    target_value: float,
    actual_value: float,
    period_start: date,
    period_end: date,
    today: date,
) -> KpiEvaluation:
    if target_value <= 0:
        raise ValueError("target_value phải lớn hơn 0")

    elapsed_ratio = compute_elapsed_ratio(period_start, period_end, today)
    expected_value = target_value * elapsed_ratio
    at_risk = expected_value > 0 and actual_value < RISK_THRESHOLD * expected_value

    if actual_value >= target_value:
        status = KpiStatus.COMPLETED
    elif at_risk:
        status = KpiStatus.AT_RISK
    else:
        status = KpiStatus.ON_TRACK

    return KpiEvaluation(
        actual_value=actual_value,
        target_value=target_value,
        expected_value=expected_value,
        elapsed_ratio=elapsed_ratio,
        percent_complete=actual_value / target_value,
        status=status,
        at_risk=at_risk,
    )
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_rules.py -v`
Expected: PASS (13 test)

- [ ] **Step 5: Commit**

```bash
git add backend/app/rules.py backend/tests/test_rules.py
git commit -m "feat(backend): luat canh bao rui ro KPI duoi dang ham thuan"
```

---

### Task 3: Mô hình dữ liệu SQLAlchemy

**Files:**
- Create: `backend/app/models.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `app.db.Base`
- Produces: enum `app.models.TaskStatus` (`todo`/`doing`/`done`), `app.models.ExtractionStatus` (`pending`/`extracted`/`failed`), `app.models.SuggestionStatus` (`pending`/`approved`/`rejected`); model `Employee`, `Kpi`, `Task`, `WeeklyReport`, `KpiUpdateSuggestion`, `TaskCompletionSuggestion`, `Blocker`, `KpiProgressEntry`; fixture pytest `db_session` (SQLAlchemy `Session` trên SQLite in-memory, dựng lại mỗi test)

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_models.py`:

```python
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Employee,
    ExtractionStatus,
    Kpi,
    KpiProgressEntry,
    Task,
    TaskStatus,
    WeeklyReport,
)


def test_can_persist_full_object_graph(db_session):
    employee = Employee(name="Nguyen Van A", email="a@example.com")
    db_session.add(employee)
    db_session.flush()

    kpi = Kpi(
        name="Hop dong ky moi",
        target_value=100.0,
        unit="hop dong",
        owner_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db_session.add(kpi)
    db_session.flush()

    task = Task(
        title="Chot hop dong voi khach X",
        kpi_id=kpi.id,
        assignee_id=employee.id,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    db_session.commit()

    assert task.id is not None
    assert task.status is TaskStatus.TODO


def test_report_defaults_to_pending_extraction(db_session):
    employee = Employee(name="B", email="b@example.com")
    db_session.add(employee)
    db_session.flush()

    report = WeeklyReport(
        employee_id=employee.id,
        week_start=date(2026, 3, 2),
        raw_text="Tuan nay lam viec X",
    )
    db_session.add(report)
    db_session.commit()

    assert report.extraction_status is ExtractionStatus.PENDING
    assert report.submitted_at is not None


def test_duplicate_employee_week_is_rejected(db_session):
    employee = Employee(name="C", email="c@example.com")
    db_session.add(employee)
    db_session.flush()

    db_session.add(
        WeeklyReport(
            employee_id=employee.id, week_start=date(2026, 3, 2), raw_text="lan 1"
        )
    )
    db_session.commit()

    db_session.add(
        WeeklyReport(
            employee_id=employee.id, week_start=date(2026, 3, 2), raw_text="lan 2"
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_same_week_different_employee_is_allowed(db_session):
    first = Employee(name="D", email="d@example.com")
    second = Employee(name="E", email="e@example.com")
    db_session.add_all([first, second])
    db_session.flush()

    db_session.add_all(
        [
            WeeklyReport(
                employee_id=first.id, week_start=date(2026, 3, 2), raw_text="x"
            ),
            WeeklyReport(
                employee_id=second.id, week_start=date(2026, 3, 2), raw_text="y"
            ),
        ]
    )
    db_session.commit()

    assert db_session.query(WeeklyReport).count() == 2


def test_progress_entries_accumulate(db_session):
    employee = Employee(name="F", email="f@example.com")
    db_session.add(employee)
    db_session.flush()
    kpi = Kpi(
        name="Doanh thu",
        target_value=1000.0,
        unit="trieu",
        owner_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db_session.add(kpi)
    db_session.flush()

    db_session.add_all(
        [
            KpiProgressEntry(
                kpi_id=kpi.id, delta_value=10.0, effective_date=date(2026, 2, 2)
            ),
            KpiProgressEntry(
                kpi_id=kpi.id, delta_value=5.5, effective_date=date(2026, 2, 9)
            ),
        ]
    )
    db_session.commit()

    total = sum(entry.delta_value for entry in kpi.progress_entries)
    assert total == 15.5
```

- [ ] **Step 2: Viết `backend/tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app import models  # noqa: F401  - nạp model để Base biết mọi bảng


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(db_engine):
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 3: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_models.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 4: Viết `backend/app/models.py`**

```python
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
```

- [ ] **Step 5: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_models.py -v`
Expected: PASS (5 test)

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py backend/tests/conftest.py backend/tests/test_models.py
git commit -m "feat(backend): mo hinh du lieu SQLAlchemy va rang buoc unique bao cao tuan"
```

---

### Task 4: Schema trích xuất và validate theo catalog

**Files:**
- Create: `backend/app/llm/__init__.py`, `backend/app/llm/base.py`
- Test: `backend/tests/test_llm_base.py`

**Interfaces:**
- Consumes: (không có)
- Produces: `app.llm.base.KpiCatalogItem` (`id: int`, `name: str`, `unit: str`, `target_value: float`), `TaskCatalogItem` (`id: int`, `title: str`), `ExtractionRequest` (`report_text: str`, `kpi_catalog: list[KpiCatalogItem]`, `task_catalog: list[TaskCatalogItem]`), `TaskDoneItem` (`task_id: int | None`, `description: str`), `KpiUpdateItem` (`kpi_id: int | None`, `delta_value: float`, `evidence: str`), `BlockerItem` (`description: str`, `related_kpi_id: int | None`), `ExtractionResult` (`tasks_done`, `kpi_updates`, `blockers`), `ExtractionError(Exception)`, `LlmProvider` (Protocol với thuộc tính `name: str` và phương thức `extract(request: ExtractionRequest) -> ExtractionResult`), `validate_extraction_result(result: ExtractionResult, request: ExtractionRequest) -> None`

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_llm_base.py`:

```python
import pytest
from pydantic import ValidationError

from app.llm.base import (
    ExtractionError,
    ExtractionRequest,
    ExtractionResult,
    KpiCatalogItem,
    KpiUpdateItem,
    TaskCatalogItem,
    validate_extraction_result,
)

REQUEST = ExtractionRequest(
    report_text="bat ky",
    kpi_catalog=[
        KpiCatalogItem(id=7, name="Hop dong ky moi", unit="hop dong", target_value=100.0)
    ],
    task_catalog=[TaskCatalogItem(id=12, title="Chot hop dong khach X")],
)


def test_parses_valid_payload():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [{"task_id": 12, "description": "xong"}],
            "kpi_updates": [
                {"kpi_id": 7, "delta_value": 5, "evidence": "ky them 5"}
            ],
            "blockers": [{"description": "thieu nguoi", "related_kpi_id": 7}],
        }
    )
    assert result.kpi_updates[0].delta_value == 5.0
    assert result.tasks_done[0].task_id == 12


def test_null_ids_are_allowed():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [{"task_id": None, "description": "viec phat sinh"}],
            "kpi_updates": [
                {"kpi_id": None, "delta_value": 3, "evidence": "khong ro KPI"}
            ],
            "blockers": [],
        }
    )
    assert result.kpi_updates[0].kpi_id is None


def test_missing_required_key_is_rejected():
    with pytest.raises(ValidationError):
        ExtractionResult.model_validate({"tasks_done": [], "kpi_updates": []})


def test_infinite_delta_is_rejected():
    with pytest.raises(ValidationError):
        ExtractionResult.model_validate(
            {
                "tasks_done": [],
                "blockers": [],
                "kpi_updates": [
                    {"kpi_id": 7, "delta_value": float("inf"), "evidence": "x"}
                ],
            }
        )


def test_unknown_kpi_id_is_rejected():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [],
            "blockers": [],
            "kpi_updates": [{"kpi_id": 999, "delta_value": 1, "evidence": "x"}],
        }
    )
    with pytest.raises(ExtractionError) as excinfo:
        validate_extraction_result(result, REQUEST)
    assert "999" in str(excinfo.value)


def test_unknown_task_id_is_rejected():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [{"task_id": 999, "description": "x"}],
            "blockers": [],
            "kpi_updates": [],
        }
    )
    with pytest.raises(ExtractionError):
        validate_extraction_result(result, REQUEST)


def test_unknown_related_kpi_id_in_blocker_is_rejected():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [],
            "blockers": [{"description": "x", "related_kpi_id": 999}],
            "kpi_updates": [],
        }
    )
    with pytest.raises(ExtractionError):
        validate_extraction_result(result, REQUEST)


def test_known_ids_pass_validation():
    result = ExtractionResult.model_validate(
        {
            "tasks_done": [{"task_id": 12, "description": "x"}],
            "blockers": [{"description": "y", "related_kpi_id": 7}],
            "kpi_updates": [{"kpi_id": 7, "delta_value": 2, "evidence": "z"}],
        }
    )
    validate_extraction_result(result, REQUEST)  # không ném lỗi


def test_gate_catches_infinite_delta_that_bypassed_pydantic():
    """Provider dựng object bằng model_construct vẫn không lách được cổng."""
    result = ExtractionResult.model_construct(
        tasks_done=[],
        blockers=[],
        kpi_updates=[
            KpiUpdateItem.model_construct(
                kpi_id=7, delta_value=float("inf"), evidence="x"
            )
        ],
    )
    with pytest.raises(ExtractionError):
        validate_extraction_result(result, REQUEST)


def test_gate_catches_nan_delta_that_bypassed_pydantic():
    result = ExtractionResult.model_construct(
        tasks_done=[],
        blockers=[],
        kpi_updates=[
            KpiUpdateItem.model_construct(
                kpi_id=7, delta_value=float("nan"), evidence="x"
            )
        ],
    )
    with pytest.raises(ExtractionError):
        validate_extraction_result(result, REQUEST)
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_llm_base.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.llm'`

- [ ] **Step 3: Tạo `backend/app/llm/__init__.py` rỗng**

- [ ] **Step 4: Viết `backend/app/llm/base.py`**

```python
"""Hợp đồng giữa ứng dụng và tầng LLM.

Module này không biết gì về SQLAlchemy: nhận Pydantic vào, trả Pydantic ra.
"""

import math
from typing import Protocol

from pydantic import BaseModel, Field


class ExtractionError(Exception):
    """Kết quả LLM không dùng được: JSON hỏng, sai schema, hoặc id ngoài catalog."""


class KpiCatalogItem(BaseModel):
    id: int
    name: str
    unit: str
    target_value: float


class TaskCatalogItem(BaseModel):
    id: int
    title: str


class ExtractionRequest(BaseModel):
    report_text: str
    kpi_catalog: list[KpiCatalogItem]
    task_catalog: list[TaskCatalogItem]


class TaskDoneItem(BaseModel):
    task_id: int | None = None
    description: str


class KpiUpdateItem(BaseModel):
    kpi_id: int | None = None
    delta_value: float = Field(allow_inf_nan=False)
    evidence: str


class BlockerItem(BaseModel):
    description: str
    related_kpi_id: int | None = None


class ExtractionResult(BaseModel):
    tasks_done: list[TaskDoneItem]
    kpi_updates: list[KpiUpdateItem]
    blockers: list[BlockerItem]


class LlmProvider(Protocol):
    name: str

    def extract(self, request: ExtractionRequest) -> ExtractionResult: ...


def validate_extraction_result(
    result: ExtractionResult, request: ExtractionRequest
) -> None:
    """Cổng kiểm tra DUY NHẤT áp lên output của MỌI provider.

    Gọi ở tầng service ngay sau `provider.extract(...)`, nên không provider nào
    tự quyết định được ràng buộc nào áp cho mình. Kiểm tra hai bất biến:

    1. Mọi id đều nằm trong catalog đã gửi cho LLM (hoặc là null).
    2. Mọi `delta_value` đều là số hữu hạn.

    Ràng buộc (2) trùng với `allow_inf_nan=False` trên `KpiUpdateItem`, và đó là
    cố ý: Pydantic chỉ chặn lúc dựng object, còn cổng này chặn cả provider dựng
    object bằng `model_construct` hoặc bằng bất kỳ đường nào bỏ qua validate.
    """
    kpi_ids = {item.id for item in request.kpi_catalog}
    task_ids = {item.id for item in request.task_catalog}

    for update in result.kpi_updates:
        if update.kpi_id is not None and update.kpi_id not in kpi_ids:
            raise ExtractionError(f"kpi_id {update.kpi_id} không có trong catalog")
        if not math.isfinite(update.delta_value):
            raise ExtractionError(
                f"delta_value không phải số hữu hạn: {update.delta_value}"
            )

    for task in result.tasks_done:
        if task.task_id is not None and task.task_id not in task_ids:
            raise ExtractionError(f"task_id {task.task_id} không có trong catalog")

    for blocker in result.blockers:
        if blocker.related_kpi_id is not None and blocker.related_kpi_id not in kpi_ids:
            raise ExtractionError(
                f"related_kpi_id {blocker.related_kpi_id} không có trong catalog"
            )
```

- [ ] **Step 5: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_llm_base.py -v`
Expected: PASS (10 test)

- [ ] **Step 6: Commit**

```bash
git add backend/app/llm backend/tests/test_llm_base.py
git commit -m "feat(backend): schema trich xuat va validate id theo catalog"
```

---

### Task 5: MockProvider và ScriptedProvider

**Files:**
- Create: `backend/app/llm/mock.py`
- Test: `backend/tests/test_llm_mock.py`

**Interfaces:**
- Consumes: `app.llm.base.ExtractionRequest`, `ExtractionResult`, `ExtractionError`, `KpiUpdateItem`, `TaskDoneItem`, `BlockerItem`
- Produces: `app.llm.mock.MockProvider` (thuộc tính `name = "mock"`, phương thức `extract(request) -> ExtractionResult`); `app.llm.mock.ScriptedProvider` (khởi tạo `ScriptedProvider(result: ExtractionResult | None = None, error: Exception | None = None)`, thuộc tính `name = "scripted"`)

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_llm_mock.py`:

```python
import pytest

from app.llm.base import (
    ExtractionError,
    ExtractionRequest,
    ExtractionResult,
    KpiCatalogItem,
    TaskCatalogItem,
)
from app.llm.mock import MockProvider, ScriptedProvider

CATALOG_KPIS = [
    KpiCatalogItem(id=7, name="Hop dong ky moi", unit="hop dong", target_value=100.0)
]
CATALOG_TASKS = [TaskCatalogItem(id=12, title="Chot hop dong khach X")]


def make_request(text: str) -> ExtractionRequest:
    return ExtractionRequest(
        report_text=text, kpi_catalog=CATALOG_KPIS, task_catalog=CATALOG_TASKS
    )


def test_matches_kpi_by_name_and_extracts_number():
    request = make_request("Tuan nay ky them 5 hop dong ky moi.")
    result = MockProvider().extract(request)
    assert len(result.kpi_updates) == 1
    assert result.kpi_updates[0].kpi_id == 7
    assert result.kpi_updates[0].delta_value == 5.0


def test_kpi_name_without_number_produces_no_update():
    request = make_request("Da trao doi ve hop dong ky moi voi khach.")
    result = MockProvider().extract(request)
    assert result.kpi_updates == []


def test_matches_task_by_title():
    request = make_request("Da chot hop dong khach X trong tuan.")
    result = MockProvider().extract(request)
    assert len(result.tasks_done) == 1
    assert result.tasks_done[0].task_id == 12


def test_detects_blocker_line():
    request = make_request("Dang vuong phe duyet tu phong phap che.")
    result = MockProvider().extract(request)
    assert len(result.blockers) == 1
    assert "phap che" in result.blockers[0].description


def test_unmatched_line_produces_nothing():
    request = make_request("Tham gia hop giao ban dau tuan.")
    result = MockProvider().extract(request)
    assert result.kpi_updates == []
    assert result.tasks_done == []
    assert result.blockers == []


def test_is_deterministic():
    request = make_request("Ky them 5 hop dong ky moi.")
    provider = MockProvider()
    assert provider.extract(request) == provider.extract(request)


def test_scripted_provider_returns_canned_result():
    canned = ExtractionResult(tasks_done=[], kpi_updates=[], blockers=[])
    assert ScriptedProvider(result=canned).extract(make_request("x")) is canned


def test_scripted_provider_raises_configured_error():
    provider = ScriptedProvider(error=ExtractionError("loi gia lap"))
    with pytest.raises(ExtractionError):
        provider.extract(make_request("x"))
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_llm_mock.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.llm.mock'`

- [ ] **Step 3: Viết `backend/app/llm/mock.py`**

```python
"""Provider giả lập, không gọi mạng. Đây là provider mặc định.

Cách hoạt động: duyệt từng dòng báo cáo, khớp tên KPI / tiêu đề Task trong
catalog bằng so khớp chuỗi, và lấy con số đầu tiên trên dòng làm delta.
Đủ thật để test trọn vòng có ý nghĩa, và hoàn toàn tất định.
"""

import re

from app.llm.base import (
    BlockerItem,
    ExtractionRequest,
    ExtractionResult,
    KpiUpdateItem,
    TaskDoneItem,
)

NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
BLOCKER_KEYWORDS = ("vuong", "vướng", "blocker", "chan ", "chặn", "kho khan", "khó khăn")


def _first_number(line: str) -> float | None:
    match = NUMBER_PATTERN.search(line)
    if match is None:
        return None
    return float(match.group().replace(",", "."))


class MockProvider:
    name = "mock"

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        tasks_done: list[TaskDoneItem] = []
        kpi_updates: list[KpiUpdateItem] = []
        blockers: list[BlockerItem] = []

        for raw_line in request.report_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lowered = line.lower()

            for kpi in request.kpi_catalog:
                if kpi.name.lower() in lowered:
                    delta = _first_number(line)
                    if delta is not None:
                        kpi_updates.append(
                            KpiUpdateItem(
                                kpi_id=kpi.id, delta_value=delta, evidence=line
                            )
                        )
                    break

            for task in request.task_catalog:
                if task.title.lower() in lowered:
                    tasks_done.append(TaskDoneItem(task_id=task.id, description=line))
                    break

            if any(keyword in lowered for keyword in BLOCKER_KEYWORDS):
                blockers.append(BlockerItem(description=line, related_kpi_id=None))

        return ExtractionResult(
            tasks_done=tasks_done, kpi_updates=kpi_updates, blockers=blockers
        )


class ScriptedProvider:
    """Provider trả về kết quả đóng sẵn — dùng khi test cần một kết quả cụ thể."""

    name = "scripted"

    def __init__(
        self,
        result: ExtractionResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        if self._error is not None:
            raise self._error
        if self._result is None:
            raise ValueError("ScriptedProvider cần result hoặc error")
        return self._result
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_llm_mock.py -v`
Expected: PASS (8 test)

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/mock.py backend/tests/test_llm_mock.py
git commit -m "feat(backend): MockProvider tat dinh va ScriptedProvider cho test"
```

---

### Task 6: AnthropicProvider và factory chọn provider

Adapter thật, dùng structured outputs của SDK Anthropic. Test tiêm một client giả nên **không chạm mạng**.

**Files:**
- Create: `backend/app/llm/prompt.py`, `backend/app/llm/anthropic_provider.py`, `backend/app/llm/factory.py`
- Test: `backend/tests/test_llm_anthropic.py`, `backend/tests/test_llm_factory.py`

**Interfaces:**
- Consumes: `app.llm.base.*`, `app.llm.mock.MockProvider`, `app.config.Settings`
- Produces: `app.llm.prompt.SYSTEM_PROMPT: str`, `app.llm.prompt.build_user_prompt(request: ExtractionRequest) -> str`; `app.llm.anthropic_provider.AnthropicProvider` (khởi tạo `AnthropicProvider(api_key: str, model: str, client=None)`, thuộc tính `name = "anthropic"`); `app.llm.factory.get_provider(settings: Settings) -> LlmProvider`

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_llm_anthropic.py`:

```python
import pytest

from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import (
    ExtractionError,
    ExtractionRequest,
    ExtractionResult,
    KpiCatalogItem,
    KpiUpdateItem,
    TaskCatalogItem,
)
from app.llm.prompt import build_user_prompt

REQUEST = ExtractionRequest(
    report_text="Ky them 5 hop dong.",
    kpi_catalog=[
        KpiCatalogItem(id=7, name="Hop dong ky moi", unit="hop dong", target_value=100.0)
    ],
    task_catalog=[TaskCatalogItem(id=12, title="Chot hop dong khach X")],
)


class FakeResponse:
    def __init__(self, parsed_output=None, stop_reason="end_turn"):
        self.parsed_output = parsed_output
        self.stop_reason = stop_reason


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.last_kwargs = None

    def parse(self, **kwargs):
        self.last_kwargs = kwargs
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.messages = FakeMessages(response=response, error=error)


def test_user_prompt_contains_catalog_and_report():
    prompt = build_user_prompt(REQUEST)
    assert "Hop dong ky moi" in prompt
    assert "Chot hop dong khach X" in prompt
    assert "Ky them 5 hop dong." in prompt
    assert "7" in prompt


def test_returns_parsed_output():
    expected = ExtractionResult(
        tasks_done=[],
        kpi_updates=[KpiUpdateItem(kpi_id=7, delta_value=5.0, evidence="Ky them 5")],
        blockers=[],
    )
    client = FakeClient(response=FakeResponse(parsed_output=expected))
    provider = AnthropicProvider(api_key="k", model="claude-sonnet-5", client=client)

    assert provider.extract(REQUEST) == expected


def test_sends_configured_model_and_output_format():
    expected = ExtractionResult(tasks_done=[], kpi_updates=[], blockers=[])
    client = FakeClient(response=FakeResponse(parsed_output=expected))
    provider = AnthropicProvider(api_key="k", model="claude-sonnet-5", client=client)

    provider.extract(REQUEST)

    kwargs = client.messages.last_kwargs
    assert kwargs["model"] == "claude-sonnet-5"
    assert kwargs["output_format"] is ExtractionResult


def test_refusal_becomes_extraction_error():
    client = FakeClient(response=FakeResponse(parsed_output=None, stop_reason="refusal"))
    provider = AnthropicProvider(api_key="k", model="claude-sonnet-5", client=client)

    with pytest.raises(ExtractionError):
        provider.extract(REQUEST)


def test_missing_parsed_output_becomes_extraction_error():
    client = FakeClient(response=FakeResponse(parsed_output=None))
    provider = AnthropicProvider(api_key="k", model="claude-sonnet-5", client=client)

    with pytest.raises(ExtractionError):
        provider.extract(REQUEST)


def test_sdk_error_becomes_extraction_error():
    client = FakeClient(error=RuntimeError("mang loi"))
    provider = AnthropicProvider(api_key="k", model="claude-sonnet-5", client=client)

    with pytest.raises(ExtractionError):
        provider.extract(REQUEST)
```

`backend/tests/test_llm_factory.py`:

```python
import pytest

from app.config import Settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.factory import get_provider
from app.llm.mock import MockProvider


def test_default_settings_give_mock_provider():
    provider = get_provider(Settings(_env_file=None))
    assert isinstance(provider, MockProvider)


def test_anthropic_provider_selected_when_configured():
    settings = Settings(
        _env_file=None, llm_provider="anthropic", anthropic_api_key="test-key"
    )
    assert isinstance(get_provider(settings), AnthropicProvider)


def test_anthropic_without_api_key_is_rejected():
    settings = Settings(_env_file=None, llm_provider="anthropic", anthropic_api_key=None)
    with pytest.raises(ValueError):
        get_provider(settings)


def test_unknown_provider_is_rejected():
    settings = Settings(_env_file=None, llm_provider="khong-ton-tai")
    with pytest.raises(ValueError):
        get_provider(settings)
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_llm_anthropic.py tests/test_llm_factory.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.llm.anthropic_provider'`

- [ ] **Step 3: Viết `backend/app/llm/prompt.py`**

```python
"""Dựng prompt cho provider thật. Catalog được nhúng vào prompt để LLM
trả về đúng id, thay vì đoán tên KPI rồi phải so khớp chuỗi ở backend.
"""

from app.llm.base import ExtractionRequest

SYSTEM_PROMPT = """Bạn là trợ lý phân tích báo cáo công việc hàng tuần.

Nhiệm vụ: đọc báo cáo tuần dạng văn bản tự do của một nhân viên và trích ra:
- tasks_done: những công việc trong danh sách Task đã được hoàn thành
- kpi_updates: mức TĂNG THÊM (delta) của từng KPI trong tuần này
- blockers: các vướng mắc, rào cản được nhắc tới

Quy tắc bắt buộc:
- Chỉ dùng id có trong danh mục được cung cấp. Nếu không chắc chắn, đặt id là null.
- delta_value là phần TĂNG THÊM trong tuần, KHÔNG phải tổng lũy kế.
- evidence phải là đoạn trích nguyên văn từ báo cáo, không diễn giải lại.
- Không bịa số liệu. Nếu báo cáo không nêu con số cụ thể, đừng tạo kpi_update."""


def build_user_prompt(request: ExtractionRequest) -> str:
    kpi_lines = [
        f"- id={item.id} | {item.name} | đơn vị: {item.unit} | chỉ tiêu: {item.target_value}"
        for item in request.kpi_catalog
    ] or ["(không có KPI nào)"]

    task_lines = [
        f"- id={item.id} | {item.title}" for item in request.task_catalog
    ] or ["(không có task nào)"]

    return (
        "DANH MỤC KPI:\n"
        + "\n".join(kpi_lines)
        + "\n\nDANH MỤC TASK:\n"
        + "\n".join(task_lines)
        + "\n\nBÁO CÁO TUẦN:\n"
        + request.report_text
    )
```

- [ ] **Step 4: Viết `backend/app/llm/anthropic_provider.py`**

```python
"""Adapter gọi Claude thật.

Dùng structured outputs: `messages.parse(output_format=ExtractionResult)` trả về
`response.parsed_output` đã được validate theo schema, nên không cần parse JSON tay.
"""

from app.llm.base import ExtractionError, ExtractionRequest, ExtractionResult
from app.llm.prompt import SYSTEM_PROMPT, build_user_prompt

MAX_TOKENS = 16000


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, client=None) -> None:
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
        self._client = client
        self._model = model

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(request)}],
                output_format=ExtractionResult,
            )
        except Exception as exc:  # lỗi mạng, rate limit, 4xx/5xx từ SDK
            raise ExtractionError(f"Gọi Anthropic thất bại: {exc}") from exc

        if getattr(response, "stop_reason", None) == "refusal":
            raise ExtractionError("Anthropic từ chối xử lý báo cáo này")

        result = getattr(response, "parsed_output", None)
        if result is None:
            raise ExtractionError("Anthropic không trả về kết quả có cấu trúc")

        return result
```

- [ ] **Step 5: Viết `backend/app/llm/factory.py`**

```python
from app.config import Settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LlmProvider
from app.llm.mock import MockProvider


def get_provider(settings: Settings) -> LlmProvider:
    if settings.llm_provider == "mock":
        return MockProvider()
    if settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("LLM_PROVIDER=anthropic nhưng thiếu ANTHROPIC_API_KEY")
        return AnthropicProvider(
            api_key=settings.anthropic_api_key, model=settings.anthropic_model
        )
    raise ValueError(f"LLM_PROVIDER không hợp lệ: {settings.llm_provider}")
```

- [ ] **Step 6: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_llm_anthropic.py tests/test_llm_factory.py -v`
Expected: PASS (10 test)

- [ ] **Step 7: Commit**

```bash
git add backend/app/llm/prompt.py backend/app/llm/anthropic_provider.py backend/app/llm/factory.py backend/tests/test_llm_anthropic.py backend/tests/test_llm_factory.py
git commit -m "feat(backend): adapter Anthropic dung structured outputs va factory chon provider"
```

---

### Task 7: Service nộp báo cáo và chạy trích xuất

**Files:**
- Create: `backend/app/errors.py`, `backend/app/services/__init__.py`, `backend/app/services/extraction.py`
- Test: `backend/tests/test_service_extraction.py`

**Interfaces:**
- Consumes: `app.models.*`, `app.llm.base.*`, `app.llm.mock.ScriptedProvider`, fixture `db_session`
- Produces: `app.errors.ConflictError(Exception)`, `app.errors.NotFoundError(Exception)`; `app.services.extraction.build_extraction_request(db: Session, report: WeeklyReport) -> ExtractionRequest`; `app.services.extraction.run_extraction(db: Session, report: WeeklyReport, provider: LlmProvider) -> WeeklyReport`; `app.services.extraction.submit_report(db: Session, *, employee_id: int, week_start: date, raw_text: str, provider: LlmProvider) -> WeeklyReport`

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_service_extraction.py`:

```python
from datetime import date

import pytest

from app.errors import ConflictError
from app.llm.base import (
    BlockerItem,
    ExtractionError,
    ExtractionResult,
    KpiUpdateItem,
    TaskDoneItem,
)
from app.llm.mock import MockProvider, ScriptedProvider
from app.models import Employee, ExtractionStatus, Kpi, Task, TaskStatus
from app.services.extraction import build_extraction_request, submit_report

WEEK = date(2026, 3, 2)


@pytest.fixture
def seeded(db_session):
    employee = Employee(name="Nguyen Van A", email="a@example.com")
    db_session.add(employee)
    db_session.flush()
    kpi = Kpi(
        name="Hop dong ky moi",
        target_value=100.0,
        unit="hop dong",
        owner_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db_session.add(kpi)
    db_session.flush()
    task = Task(
        title="Chot hop dong khach X",
        kpi_id=kpi.id,
        assignee_id=employee.id,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    db_session.commit()
    return {"employee": employee, "kpi": kpi, "task": task}


def test_catalog_contains_employee_kpis_and_open_tasks(db_session, seeded):
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="trong",
        provider=MockProvider(),
    )
    request = build_extraction_request(db_session, report)

    assert [item.id for item in request.kpi_catalog] == [seeded["kpi"].id]
    assert [item.id for item in request.task_catalog] == [seeded["task"].id]


def test_done_tasks_are_excluded_from_catalog(db_session, seeded):
    seeded["task"].status = TaskStatus.DONE
    db_session.commit()

    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="trong",
        provider=MockProvider(),
    )
    request = build_extraction_request(db_session, report)

    assert request.task_catalog == []


def test_successful_extraction_creates_suggestions(db_session, seeded):
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text=(
            "Ky them 5 hop dong ky moi.\n"
            "Da chot hop dong khach X.\n"
            "Dang vuong phe duyet phap che."
        ),
        provider=MockProvider(),
    )

    assert report.extraction_status is ExtractionStatus.EXTRACTED
    assert report.provider_name == "mock"
    assert len(report.kpi_suggestions) == 1
    assert report.kpi_suggestions[0].suggested_delta == 5.0
    assert report.kpi_suggestions[0].suggested_kpi_id == seeded["kpi"].id
    assert len(report.task_suggestions) == 1
    assert len(report.blockers) == 1


def test_suggestions_start_pending_with_empty_final_fields(db_session, seeded):
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="Ky them 5 hop dong ky moi.",
        provider=MockProvider(),
    )
    suggestion = report.kpi_suggestions[0]

    assert suggestion.status.value == "pending"
    assert suggestion.final_kpi_id is None
    assert suggestion.final_delta is None


def test_provider_error_marks_report_failed_without_suggestions(db_session, seeded):
    provider = ScriptedProvider(error=ExtractionError("LLM tra ve rac"))
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="bat ky",
        provider=provider,
    )

    assert report.extraction_status is ExtractionStatus.FAILED
    assert "rac" in report.extraction_error
    assert report.kpi_suggestions == []
    assert report.task_suggestions == []
    assert report.blockers == []


def test_kpi_id_outside_catalog_marks_report_failed(db_session, seeded):
    """Provider trả kpi_id không có trong catalog -> bao cao failed, khong suggestion."""
    provider = ScriptedProvider(
        result=ExtractionResult(
            tasks_done=[],
            blockers=[],
            kpi_updates=[
                KpiUpdateItem(kpi_id=99999, delta_value=1.0, evidence="ngoai catalog")
            ],
        )
    )
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="bat ky",
        provider=provider,
    )

    assert report.extraction_status is ExtractionStatus.FAILED
    assert "99999" in report.extraction_error
    assert report.kpi_suggestions == []
    assert report.blockers == []


def test_task_id_outside_catalog_marks_report_failed(db_session, seeded):
    provider = ScriptedProvider(
        result=ExtractionResult(
            tasks_done=[TaskDoneItem(task_id=99999, description="ngoai catalog")],
            blockers=[],
            kpi_updates=[],
        )
    )
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="bat ky",
        provider=provider,
    )

    assert report.extraction_status is ExtractionStatus.FAILED
    assert report.task_suggestions == []


def test_non_finite_delta_marks_report_failed(db_session, seeded):
    """Provider lach Pydantic bang model_construct van bi cong service chan lai."""
    provider = ScriptedProvider(
        result=ExtractionResult.model_construct(
            tasks_done=[],
            blockers=[],
            kpi_updates=[
                KpiUpdateItem.model_construct(
                    kpi_id=seeded["kpi"].id, delta_value=float("inf"), evidence="x"
                )
            ],
        )
    )
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="bat ky",
        provider=provider,
    )

    assert report.extraction_status is ExtractionStatus.FAILED
    assert report.kpi_suggestions == []


def test_null_ids_are_persisted_as_null(db_session, seeded):
    provider = ScriptedProvider(
        result=ExtractionResult(
            tasks_done=[TaskDoneItem(task_id=None, description="viec phat sinh")],
            blockers=[BlockerItem(description="thieu nguoi", related_kpi_id=None)],
            kpi_updates=[
                KpiUpdateItem(kpi_id=None, delta_value=3.0, evidence="khong ro KPI")
            ],
        )
    )
    report = submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="bat ky",
        provider=provider,
    )

    assert report.extraction_status is ExtractionStatus.EXTRACTED
    assert report.kpi_suggestions[0].suggested_kpi_id is None
    assert report.task_suggestions[0].suggested_task_id is None


def test_duplicate_report_raises_conflict(db_session, seeded):
    submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="lan 1",
        provider=MockProvider(),
    )

    with pytest.raises(ConflictError):
        submit_report(
            db_session,
            employee_id=seeded["employee"].id,
            week_start=WEEK,
            raw_text="lan 2",
            provider=MockProvider(),
        )


def test_duplicate_report_does_not_create_second_row(db_session, seeded):
    from app.models import WeeklyReport

    submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text="lan 1",
        provider=MockProvider(),
    )
    with pytest.raises(ConflictError):
        submit_report(
            db_session,
            employee_id=seeded["employee"].id,
            week_start=WEEK,
            raw_text="lan 2",
            provider=MockProvider(),
        )

    assert db_session.query(WeeklyReport).count() == 1
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_service_extraction.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.errors'`

- [ ] **Step 3: Viết `backend/app/errors.py`**

```python
"""Lỗi nghiệp vụ, không phụ thuộc HTTP. `main.py` ánh xạ chúng sang mã trạng thái."""


class ConflictError(Exception):
    """Thao tác không hợp lệ với trạng thái hiện tại (→ HTTP 409)."""


class NotFoundError(Exception):
    """Không tìm thấy bản ghi (→ HTTP 404)."""
```

- [ ] **Step 4: Tạo `backend/app/services/__init__.py` rỗng**

- [ ] **Step 5: Viết `backend/app/services/extraction.py`**

```python
from datetime import date

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ConflictError
from app.llm.base import (
    ExtractionError,
    ExtractionRequest,
    KpiCatalogItem,
    LlmProvider,
    TaskCatalogItem,
    validate_extraction_result,
)
from app.models import (
    Blocker,
    ExtractionStatus,
    Kpi,
    KpiUpdateSuggestion,
    Task,
    TaskCompletionSuggestion,
    TaskStatus,
    WeeklyReport,
)


def build_extraction_request(db: Session, report: WeeklyReport) -> ExtractionRequest:
    """Catalog gồm KPI do nhân viên phụ trách và Task của họ chưa hoàn thành."""
    kpis = db.scalars(select(Kpi).where(Kpi.owner_id == report.employee_id)).all()
    tasks = db.scalars(
        select(Task).where(
            Task.assignee_id == report.employee_id, Task.status != TaskStatus.DONE
        )
    ).all()

    return ExtractionRequest(
        report_text=report.raw_text,
        kpi_catalog=[
            KpiCatalogItem(
                id=kpi.id, name=kpi.name, unit=kpi.unit, target_value=kpi.target_value
            )
            for kpi in kpis
        ],
        task_catalog=[TaskCatalogItem(id=task.id, title=task.title) for task in tasks],
    )


def run_extraction(
    db: Session, report: WeeklyReport, provider: LlmProvider
) -> WeeklyReport:
    """Gọi provider và ghi kết quả. Thất bại → failed, không tạo suggestion nào.

    `validate_extraction_result` được gọi ở đây, sau MỌI provider, nên không
    provider nào tự miễn trừ được ràng buộc catalog và delta hữu hạn.
    `ValidationError` cũng được bắt: một provider ném lỗi Pydantic thì báo cáo
    phải thành `failed`, chứ không được làm sập request.
    """
    request = build_extraction_request(db, report)
    report.provider_name = provider.name

    try:
        result = provider.extract(request)
        validate_extraction_result(result, request)
    except (ExtractionError, ValidationError) as exc:
        report.extraction_status = ExtractionStatus.FAILED
        report.extraction_error = str(exc)
        db.commit()
        return report

    for update in result.kpi_updates:
        db.add(
            KpiUpdateSuggestion(
                report_id=report.id,
                suggested_kpi_id=update.kpi_id,
                suggested_delta=update.delta_value,
                evidence=update.evidence,
            )
        )
    for task_done in result.tasks_done:
        db.add(
            TaskCompletionSuggestion(
                report_id=report.id,
                suggested_task_id=task_done.task_id,
                raw_text=task_done.description,
            )
        )
    for blocker in result.blockers:
        db.add(
            Blocker(
                report_id=report.id,
                description=blocker.description,
                related_kpi_id=blocker.related_kpi_id,
            )
        )

    report.extraction_status = ExtractionStatus.EXTRACTED
    report.extraction_error = None
    report.raw_llm_response = result.model_dump_json()
    db.commit()
    db.refresh(report)
    return report


def submit_report(
    db: Session,
    *,
    employee_id: int,
    week_start: date,
    raw_text: str,
    provider: LlmProvider,
) -> WeeklyReport:
    existing = db.scalar(
        select(WeeklyReport).where(
            WeeklyReport.employee_id == employee_id,
            WeeklyReport.week_start == week_start,
        )
    )
    if existing is not None:
        raise ConflictError("Nhân viên này đã nộp báo cáo cho tuần đó")

    report = WeeklyReport(
        employee_id=employee_id, week_start=week_start, raw_text=raw_text
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return run_extraction(db, report, provider)
```

- [ ] **Step 6: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_service_extraction.py -v`
Expected: PASS (11 test)

- [ ] **Step 7: Commit**

```bash
git add backend/app/errors.py backend/app/services backend/tests/test_service_extraction.py
git commit -m "feat(backend): service nop bao cao va chay trich xuat dong bo"
```

---

### Task 8: Trích lại báo cáo (điều kiện và dọn dẹp)

Theo mục 7.3 của spec. Điều kiện quét **cả hai** bảng suggestion.

**Files:**
- Modify: `backend/app/services/extraction.py` (thêm hàm mới ở cuối file)
- Test: `backend/tests/test_service_reextraction.py`

**Interfaces:**
- Consumes: `app.services.extraction.run_extraction`, `app.errors.ConflictError`, `app.models.SuggestionStatus`
- Produces: `app.services.extraction.reextract_report(db: Session, report: WeeklyReport, provider: LlmProvider) -> WeeklyReport`

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_service_reextraction.py`:

```python
from datetime import date

import pytest

from app.errors import ConflictError
from app.llm.base import ExtractionError, ExtractionResult
from app.llm.mock import MockProvider, ScriptedProvider
from app.models import (
    Blocker,
    Employee,
    ExtractionStatus,
    Kpi,
    KpiUpdateSuggestion,
    SuggestionStatus,
    Task,
    TaskCompletionSuggestion,
    TaskStatus,
)
from app.services.extraction import reextract_report, submit_report

WEEK = date(2026, 3, 2)
REPORT_TEXT = (
    "Ky them 5 hop dong ky moi.\n"
    "Da chot hop dong khach X.\n"
    "Dang vuong phe duyet phap che."
)


@pytest.fixture
def seeded(db_session):
    employee = Employee(name="A", email="a@example.com")
    db_session.add(employee)
    db_session.flush()
    kpi = Kpi(
        name="Hop dong ky moi",
        target_value=100.0,
        unit="hop dong",
        owner_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db_session.add(kpi)
    db_session.flush()
    task = Task(
        title="Chot hop dong khach X",
        kpi_id=kpi.id,
        assignee_id=employee.id,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    db_session.commit()
    return {"employee": employee, "kpi": kpi, "task": task}


def make_report(db_session, seeded, provider):
    return submit_report(
        db_session,
        employee_id=seeded["employee"].id,
        week_start=WEEK,
        raw_text=REPORT_TEXT,
        provider=provider,
    )


def test_failed_report_can_be_reextracted(db_session, seeded):
    report = make_report(
        db_session, seeded, ScriptedProvider(error=ExtractionError("hong"))
    )
    assert report.extraction_status is ExtractionStatus.FAILED

    report = reextract_report(db_session, report, MockProvider())

    assert report.extraction_status is ExtractionStatus.EXTRACTED
    assert len(report.kpi_suggestions) == 1


def test_extracted_report_without_approvals_can_be_reextracted(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())
    old_ids = {s.id for s in report.kpi_suggestions}

    report = reextract_report(db_session, report, MockProvider())

    new_ids = {s.id for s in report.kpi_suggestions}
    assert new_ids.isdisjoint(old_ids)
    assert len(report.kpi_suggestions) == 1


def test_reextraction_deletes_pending_suggestions(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())

    reextract_report(
        db_session,
        report,
        ScriptedProvider(
            result=ExtractionResult(tasks_done=[], kpi_updates=[], blockers=[])
        ),
    )

    assert db_session.query(KpiUpdateSuggestion).count() == 0
    assert db_session.query(TaskCompletionSuggestion).count() == 0


def test_reextraction_keeps_rejected_suggestions(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())
    rejected = report.kpi_suggestions[0]
    rejected.status = SuggestionStatus.REJECTED
    db_session.commit()
    rejected_id = rejected.id

    reextract_report(db_session, report, MockProvider())

    survivor = db_session.get(KpiUpdateSuggestion, rejected_id)
    assert survivor is not None
    assert survivor.status is SuggestionStatus.REJECTED


def test_reextraction_recreates_blockers(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())
    old_ids = {b.id for b in report.blockers}

    report = reextract_report(db_session, report, MockProvider())

    assert len(report.blockers) == 1
    assert {b.id for b in report.blockers}.isdisjoint(old_ids)
    assert db_session.query(Blocker).count() == 1


def test_approved_kpi_suggestion_blocks_reextraction(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())
    report.kpi_suggestions[0].status = SuggestionStatus.APPROVED
    db_session.commit()

    with pytest.raises(ConflictError):
        reextract_report(db_session, report, MockProvider())


def test_approved_task_suggestion_also_blocks_reextraction(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())
    report.task_suggestions[0].status = SuggestionStatus.APPROVED
    db_session.commit()

    with pytest.raises(ConflictError):
        reextract_report(db_session, report, MockProvider())


def test_blocked_reextraction_changes_nothing(db_session, seeded):
    report = make_report(db_session, seeded, MockProvider())
    report.task_suggestions[0].status = SuggestionStatus.APPROVED
    db_session.commit()
    kpi_ids_before = {s.id for s in report.kpi_suggestions}
    blocker_ids_before = {b.id for b in report.blockers}

    with pytest.raises(ConflictError):
        reextract_report(db_session, report, MockProvider())

    db_session.refresh(report)
    assert {s.id for s in report.kpi_suggestions} == kpi_ids_before
    assert {b.id for b in report.blockers} == blocker_ids_before
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_service_reextraction.py -v`
Expected: FAIL với `ImportError: cannot import name 'reextract_report'`

- [ ] **Step 3: Thêm `reextract_report` vào cuối `backend/app/services/extraction.py`**

Bổ sung `SuggestionStatus` vào khối import từ `app.models`, rồi thêm:

```python
def _has_approved_suggestion(db: Session, report_id: int) -> bool:
    """Quét CẢ HAI bảng suggestion — một dòng approved ở bất kỳ bảng nào cũng tính."""
    approved_kpi = db.scalar(
        select(KpiUpdateSuggestion.id).where(
            KpiUpdateSuggestion.report_id == report_id,
            KpiUpdateSuggestion.status == SuggestionStatus.APPROVED,
        )
    )
    if approved_kpi is not None:
        return True
    approved_task = db.scalar(
        select(TaskCompletionSuggestion.id).where(
            TaskCompletionSuggestion.report_id == report_id,
            TaskCompletionSuggestion.status == SuggestionStatus.APPROVED,
        )
    )
    return approved_task is not None


def reextract_report(
    db: Session, report: WeeklyReport, provider: LlmProvider
) -> WeeklyReport:
    """Chạy lại trích xuất cho một báo cáo.

    Cho phép khi báo cáo đang `failed`, HOẶC khi chưa có suggestion nào được
    duyệt. Một dòng đã duyệt là khoá báo cáo lại, vì số liệu đã vào sổ cái.
    """
    if (
        report.extraction_status is not ExtractionStatus.FAILED
        and _has_approved_suggestion(db, report.id)
    ):
        raise ConflictError(
            "Báo cáo đã có đề xuất được duyệt nên không thể trích xuất lại"
        )

    for suggestion in list(report.kpi_suggestions):
        if suggestion.status is SuggestionStatus.PENDING:
            db.delete(suggestion)
    for suggestion in list(report.task_suggestions):
        if suggestion.status is SuggestionStatus.PENDING:
            db.delete(suggestion)
    for blocker in list(report.blockers):
        db.delete(blocker)

    report.extraction_status = ExtractionStatus.PENDING
    report.extraction_error = None
    report.raw_llm_response = None
    db.commit()
    db.refresh(report)

    return run_extraction(db, report, provider)
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_service_reextraction.py -v`
Expected: PASS (8 test)

- [ ] **Step 5: Chạy toàn bộ test để chắc chắn không phá vỡ gì**

Run: `pytest -v`
Expected: PASS toàn bộ

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/extraction.py backend/tests/test_service_reextraction.py
git commit -m "feat(backend): trich lai bao cao voi dieu kien khoa va don dep suggestion"
```

---

### Task 9: Service duyệt (transactional)

**Files:**
- Create: `backend/app/services/approval.py`
- Test: `backend/tests/test_service_approval.py`

**Interfaces:**
- Consumes: `app.models.*`, `app.errors.ConflictError`, `app.errors.NotFoundError`
- Produces: `app.services.approval.approve_kpi_suggestion(db: Session, *, suggestion_id: int, final_kpi_id: int, final_delta: float, note: str | None = None) -> KpiUpdateSuggestion`; `reject_kpi_suggestion(db: Session, *, suggestion_id: int, note: str | None = None) -> KpiUpdateSuggestion`; `approve_task_suggestion(db: Session, *, suggestion_id: int, final_task_id: int) -> TaskCompletionSuggestion`; `reject_task_suggestion(db: Session, *, suggestion_id: int) -> TaskCompletionSuggestion`

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_service_approval.py`:

```python
from datetime import date, datetime

import pytest

from app.errors import ConflictError, NotFoundError
from app.llm.mock import MockProvider
from app.models import (
    Employee,
    Kpi,
    KpiProgressEntry,
    SuggestionStatus,
    Task,
    TaskStatus,
)
from app.services.approval import (
    approve_kpi_suggestion,
    approve_task_suggestion,
    reject_kpi_suggestion,
    reject_task_suggestion,
)
from app.services.extraction import submit_report

WEEK = date(2026, 3, 2)


@pytest.fixture
def report(db_session):
    employee = Employee(name="A", email="a@example.com")
    db_session.add(employee)
    db_session.flush()
    kpi = Kpi(
        name="Hop dong ky moi",
        target_value=100.0,
        unit="hop dong",
        owner_id=employee.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    db_session.add(kpi)
    db_session.flush()
    task = Task(
        title="Chot hop dong khach X",
        kpi_id=kpi.id,
        assignee_id=employee.id,
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    db_session.commit()

    return submit_report(
        db_session,
        employee_id=employee.id,
        week_start=WEEK,
        raw_text="Ky them 5 hop dong ky moi.\nDa chot hop dong khach X.",
        provider=MockProvider(),
    )


def test_approving_writes_ledger_entry(db_session, report):
    suggestion = report.kpi_suggestions[0]

    approve_kpi_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_kpi_id=suggestion.suggested_kpi_id,
        final_delta=5.0,
    )

    entries = db_session.query(KpiProgressEntry).all()
    assert len(entries) == 1
    assert entries[0].delta_value == 5.0
    assert entries[0].source_suggestion_id == suggestion.id
    assert entries[0].effective_date == WEEK


def test_approving_marks_suggestion_approved(db_session, report):
    suggestion = report.kpi_suggestions[0]

    updated = approve_kpi_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_kpi_id=suggestion.suggested_kpi_id,
        final_delta=5.0,
        note="ok",
    )

    assert updated.status is SuggestionStatus.APPROVED
    assert updated.reviewed_at is not None
    assert updated.review_note == "ok"


def test_edited_delta_is_used_not_suggested(db_session, report):
    suggestion = report.kpi_suggestions[0]
    assert suggestion.suggested_delta == 5.0

    updated = approve_kpi_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_kpi_id=suggestion.suggested_kpi_id,
        final_delta=3.0,
    )

    entry = db_session.query(KpiProgressEntry).one()
    assert entry.delta_value == 3.0
    assert updated.suggested_delta == 5.0  # bản gốc không bị ghi đè
    assert updated.final_delta == 3.0


def test_rejecting_writes_no_ledger_entry(db_session, report):
    suggestion = report.kpi_suggestions[0]

    updated = reject_kpi_suggestion(db_session, suggestion_id=suggestion.id)

    assert updated.status is SuggestionStatus.REJECTED
    assert db_session.query(KpiProgressEntry).count() == 0


def test_double_approval_raises_conflict(db_session, report):
    suggestion = report.kpi_suggestions[0]
    approve_kpi_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_kpi_id=suggestion.suggested_kpi_id,
        final_delta=5.0,
    )

    with pytest.raises(ConflictError):
        approve_kpi_suggestion(
            db_session,
            suggestion_id=suggestion.id,
            final_kpi_id=suggestion.suggested_kpi_id,
            final_delta=5.0,
        )

    assert db_session.query(KpiProgressEntry).count() == 1


def test_approving_rejected_suggestion_raises_conflict(db_session, report):
    suggestion = report.kpi_suggestions[0]
    reject_kpi_suggestion(db_session, suggestion_id=suggestion.id)

    with pytest.raises(ConflictError):
        approve_kpi_suggestion(
            db_session,
            suggestion_id=suggestion.id,
            final_kpi_id=suggestion.suggested_kpi_id,
            final_delta=5.0,
        )


def test_unknown_suggestion_raises_not_found(db_session, report):
    with pytest.raises(NotFoundError):
        reject_kpi_suggestion(db_session, suggestion_id=999999)


def test_unknown_final_kpi_raises_not_found(db_session, report):
    suggestion = report.kpi_suggestions[0]

    with pytest.raises(NotFoundError):
        approve_kpi_suggestion(
            db_session,
            suggestion_id=suggestion.id,
            final_kpi_id=999999,
            final_delta=5.0,
        )


def test_failure_mid_approval_rolls_back_everything(db_session, report, monkeypatch):
    """Nếu ghi sổ cái hỏng, suggestion phải quay về pending."""
    suggestion = report.kpi_suggestions[0]

    def explode(*args, **kwargs):
        raise RuntimeError("o dia loi")

    monkeypatch.setattr("app.services.approval.KpiProgressEntry", explode)

    with pytest.raises(RuntimeError):
        approve_kpi_suggestion(
            db_session,
            suggestion_id=suggestion.id,
            final_kpi_id=suggestion.suggested_kpi_id,
            final_delta=5.0,
        )

    db_session.expire_all()
    assert suggestion.status is SuggestionStatus.PENDING
    assert suggestion.final_delta is None
    assert db_session.query(KpiProgressEntry).count() == 0


def test_approving_task_marks_it_done(db_session, report):
    suggestion = report.task_suggestions[0]

    updated = approve_task_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_task_id=suggestion.suggested_task_id,
    )

    task = db_session.get(Task, suggestion.suggested_task_id)
    assert updated.status is SuggestionStatus.APPROVED
    assert task.status is TaskStatus.DONE
    assert task.completed_at is not None


def test_rejecting_task_leaves_it_untouched(db_session, report):
    suggestion = report.task_suggestions[0]
    task_id = suggestion.suggested_task_id

    reject_task_suggestion(db_session, suggestion_id=suggestion.id)

    task = db_session.get(Task, task_id)
    assert task.status is TaskStatus.TODO
    assert task.completed_at is None


def test_approving_already_done_task_keeps_completed_at(db_session, report):
    suggestion = report.task_suggestions[0]
    task = db_session.get(Task, suggestion.suggested_task_id)
    task.status = TaskStatus.DONE
    task.completed_at = datetime(2026, 1, 1)  # cột là DateTime, không phải Date
    db_session.commit()
    original = task.completed_at

    approve_task_suggestion(
        db_session, suggestion_id=suggestion.id, final_task_id=task.id
    )

    db_session.refresh(task)
    assert task.completed_at == original


def test_double_task_approval_raises_conflict(db_session, report):
    suggestion = report.task_suggestions[0]
    approve_task_suggestion(
        db_session,
        suggestion_id=suggestion.id,
        final_task_id=suggestion.suggested_task_id,
    )

    with pytest.raises(ConflictError):
        approve_task_suggestion(
            db_session,
            suggestion_id=suggestion.id,
            final_task_id=suggestion.suggested_task_id,
        )
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_service_approval.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.services.approval'`

- [ ] **Step 3: Viết `backend/app/services/approval.py`**

```python
"""Duyệt đề xuất. Mỗi hàm là một giao dịch: hoặc cả hai thay đổi cùng được ghi,
hoặc không gì được ghi. Không bao giờ có suggestion `approved` mà sổ cái thiếu dòng.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import (
    Kpi,
    KpiProgressEntry,
    KpiUpdateSuggestion,
    SuggestionStatus,
    Task,
    TaskCompletionSuggestion,
    TaskStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_pending_kpi_suggestion(db: Session, suggestion_id: int) -> KpiUpdateSuggestion:
    suggestion = db.get(KpiUpdateSuggestion, suggestion_id)
    if suggestion is None:
        raise NotFoundError(f"Không tìm thấy đề xuất KPI {suggestion_id}")
    if suggestion.status is not SuggestionStatus.PENDING:
        raise ConflictError("Đề xuất này đã được xử lý")
    return suggestion


def _load_pending_task_suggestion(
    db: Session, suggestion_id: int
) -> TaskCompletionSuggestion:
    suggestion = db.get(TaskCompletionSuggestion, suggestion_id)
    if suggestion is None:
        raise NotFoundError(f"Không tìm thấy đề xuất task {suggestion_id}")
    if suggestion.status is not SuggestionStatus.PENDING:
        raise ConflictError("Đề xuất này đã được xử lý")
    return suggestion


def approve_kpi_suggestion(
    db: Session,
    *,
    suggestion_id: int,
    final_kpi_id: int,
    final_delta: float,
    note: str | None = None,
) -> KpiUpdateSuggestion:
    suggestion = _load_pending_kpi_suggestion(db, suggestion_id)
    if db.get(Kpi, final_kpi_id) is None:
        raise NotFoundError(f"Không tìm thấy KPI {final_kpi_id}")

    try:
        suggestion.final_kpi_id = final_kpi_id
        suggestion.final_delta = final_delta
        suggestion.review_note = note
        suggestion.status = SuggestionStatus.APPROVED
        suggestion.reviewed_at = _utcnow()
        db.add(
            KpiProgressEntry(
                kpi_id=final_kpi_id,
                delta_value=final_delta,
                source_suggestion_id=suggestion.id,
                effective_date=suggestion.report.week_start,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(suggestion)
    return suggestion


def reject_kpi_suggestion(
    db: Session, *, suggestion_id: int, note: str | None = None
) -> KpiUpdateSuggestion:
    suggestion = _load_pending_kpi_suggestion(db, suggestion_id)
    try:
        suggestion.status = SuggestionStatus.REJECTED
        suggestion.review_note = note
        suggestion.reviewed_at = _utcnow()
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(suggestion)
    return suggestion


def approve_task_suggestion(
    db: Session, *, suggestion_id: int, final_task_id: int
) -> TaskCompletionSuggestion:
    suggestion = _load_pending_task_suggestion(db, suggestion_id)
    task = db.get(Task, final_task_id)
    if task is None:
        raise NotFoundError(f"Không tìm thấy task {final_task_id}")

    try:
        suggestion.final_task_id = final_task_id
        suggestion.status = SuggestionStatus.APPROVED
        suggestion.reviewed_at = _utcnow()
        if task.status is not TaskStatus.DONE:
            task.status = TaskStatus.DONE
            task.completed_at = _utcnow()
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(suggestion)
    return suggestion


def reject_task_suggestion(
    db: Session, *, suggestion_id: int
) -> TaskCompletionSuggestion:
    suggestion = _load_pending_task_suggestion(db, suggestion_id)
    try:
        suggestion.status = SuggestionStatus.REJECTED
        suggestion.reviewed_at = _utcnow()
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(suggestion)
    return suggestion
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_service_approval.py -v`
Expected: PASS (13 test)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/approval.py backend/tests/test_service_approval.py
git commit -m "feat(backend): service duyet de xuat ghi so cai trong mot transaction"
```

---

### Task 10: Service dashboard

**Files:**
- Create: `backend/app/services/dashboard.py`
- Test: `backend/tests/test_service_dashboard.py`

**Interfaces:**
- Consumes: `app.models.*`, `app.rules.evaluate_kpi`, `app.rules.KpiEvaluation`
- Produces: `app.services.dashboard.DashboardItem` (dataclass đông cứng: `kpi_id: int`, `kpi_name: str`, `unit: str`, `owner_name: str`, `period_start: date`, `period_end: date`, `evaluation: KpiEvaluation`); `app.services.dashboard.current_values(db: Session) -> dict[int, float]`; `app.services.dashboard.build_dashboard(db: Session, today: date) -> list[DashboardItem]`

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_service_dashboard.py`:

```python
from datetime import date

import pytest

from app.models import Employee, Kpi, KpiProgressEntry
from app.rules import KpiStatus
from app.services.dashboard import build_dashboard, current_values

START = date(2026, 1, 1)
END = date(2026, 1, 11)
MIDWAY = date(2026, 1, 6)


@pytest.fixture
def kpi(db_session):
    employee = Employee(name="Nguyen Van A", email="a@example.com")
    db_session.add(employee)
    db_session.flush()
    kpi = Kpi(
        name="Hop dong ky moi",
        target_value=100.0,
        unit="hop dong",
        owner_id=employee.id,
        period_start=START,
        period_end=END,
    )
    db_session.add(kpi)
    db_session.commit()
    return kpi


def test_kpi_without_entries_has_zero_actual(db_session, kpi):
    assert current_values(db_session) == {}

    items = build_dashboard(db_session, today=MIDWAY)
    assert items[0].evaluation.actual_value == 0.0


def test_current_value_sums_entries(db_session, kpi):
    db_session.add_all(
        [
            KpiProgressEntry(kpi_id=kpi.id, delta_value=10.0, effective_date=START),
            KpiProgressEntry(kpi_id=kpi.id, delta_value=5.5, effective_date=START),
        ]
    )
    db_session.commit()

    assert current_values(db_session) == {kpi.id: 15.5}


def test_dashboard_flags_at_risk(db_session, kpi):
    db_session.add(
        KpiProgressEntry(kpi_id=kpi.id, delta_value=10.0, effective_date=START)
    )
    db_session.commit()

    item = build_dashboard(db_session, today=MIDWAY)[0]

    assert item.evaluation.expected_value == 50.0
    assert item.evaluation.status is KpiStatus.AT_RISK


def test_dashboard_clears_warning_once_enough_progress(db_session, kpi):
    db_session.add(
        KpiProgressEntry(kpi_id=kpi.id, delta_value=60.0, effective_date=START)
    )
    db_session.commit()

    item = build_dashboard(db_session, today=MIDWAY)[0]

    assert item.evaluation.at_risk is False
    assert item.evaluation.status is KpiStatus.ON_TRACK


def test_dashboard_includes_metadata(db_session, kpi):
    item = build_dashboard(db_session, today=MIDWAY)[0]

    assert item.kpi_id == kpi.id
    assert item.kpi_name == "Hop dong ky moi"
    assert item.unit == "hop dong"
    assert item.owner_name == "Nguyen Van A"
    assert item.period_start == START


def test_entries_of_other_kpi_do_not_leak(db_session, kpi):
    other = Kpi(
        name="Doanh thu",
        target_value=1000.0,
        unit="trieu",
        owner_id=kpi.owner_id,
        period_start=START,
        period_end=END,
    )
    db_session.add(other)
    db_session.flush()
    db_session.add_all(
        [
            KpiProgressEntry(kpi_id=kpi.id, delta_value=10.0, effective_date=START),
            KpiProgressEntry(kpi_id=other.id, delta_value=999.0, effective_date=START),
        ]
    )
    db_session.commit()

    values = current_values(db_session)
    assert values[kpi.id] == 10.0
    assert values[other.id] == 999.0
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_service_dashboard.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'app.services.dashboard'`

- [ ] **Step 3: Viết `backend/app/services/dashboard.py`**

```python
"""Dashboard. `current_value` luôn được tính từ sổ cái, không có cột lưu sẵn."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Kpi, KpiProgressEntry
from app.rules import KpiEvaluation, evaluate_kpi


@dataclass(frozen=True)
class DashboardItem:
    kpi_id: int
    kpi_name: str
    unit: str
    owner_name: str
    period_start: date
    period_end: date
    evaluation: KpiEvaluation


def current_values(db: Session) -> dict[int, float]:
    """Tổng delta đã duyệt của từng KPI. KPI chưa có dòng nào sẽ không xuất hiện."""
    rows = db.execute(
        select(KpiProgressEntry.kpi_id, func.sum(KpiProgressEntry.delta_value)).group_by(
            KpiProgressEntry.kpi_id
        )
    ).all()
    return {kpi_id: float(total) for kpi_id, total in rows}


def build_dashboard(db: Session, today: date) -> list[DashboardItem]:
    totals = current_values(db)
    kpis = db.scalars(select(Kpi).order_by(Kpi.id)).all()

    return [
        DashboardItem(
            kpi_id=kpi.id,
            kpi_name=kpi.name,
            unit=kpi.unit,
            owner_name=kpi.owner.name,
            period_start=kpi.period_start,
            period_end=kpi.period_end,
            evaluation=evaluate_kpi(
                target_value=kpi.target_value,
                actual_value=totals.get(kpi.id, 0.0),
                period_start=kpi.period_start,
                period_end=kpi.period_end,
                today=today,
            ),
        )
        for kpi in kpis
    ]
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_service_dashboard.py -v`
Expected: PASS (6 test)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/dashboard.py backend/tests/test_service_dashboard.py
git commit -m "feat(backend): service dashboard tinh current_value tu so cai"
```

---

### Task 11: HTTP schemas và router CRUD (employees, kpis, tasks)

**Files:**
- Create: `backend/app/schemas.py`, `backend/app/routers/__init__.py`, `backend/app/routers/employees.py`, `backend/app/routers/kpis.py`, `backend/app/routers/tasks.py`
- Modify: `backend/app/main.py` (gắn router và exception handler), `backend/tests/conftest.py` (thêm fixture `api_client`)
- Test: `backend/tests/test_api_crud.py`

**Interfaces:**
- Consumes: `app.models.*`, `app.errors.*`, `app.db.get_db`
- Produces: `app.schemas.EmployeeCreate` / `EmployeeOut`, `KpiCreate` / `KpiUpdate` / `KpiOut`, `TaskCreate` / `TaskUpdate` / `TaskOut`; router object `router` trong mỗi file `app/routers/*.py`; fixture pytest `api_client` (một `TestClient` đã ghi đè `get_db` sang SQLite in-memory)

- [ ] **Step 1: Thêm fixture `api_client` vào `backend/tests/conftest.py`**

```python
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app


@pytest.fixture
def api_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Viết test thất bại**

`backend/tests/test_api_crud.py`:

```python
def create_employee(client, email="a@example.com"):
    response = client.post(
        "/api/employees", json={"name": "Nguyen Van A", "email": email}
    )
    assert response.status_code == 201
    return response.json()


def create_kpi(client, owner_id):
    response = client.post(
        "/api/kpis",
        json={
            "name": "Hop dong ky moi",
            "target_value": 100.0,
            "unit": "hop dong",
            "owner_id": owner_id,
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_and_list_employees(api_client):
    created = create_employee(api_client)
    assert created["id"] > 0

    listed = api_client.get("/api/employees").json()
    assert [item["email"] for item in listed] == ["a@example.com"]


def test_create_and_get_kpi(api_client):
    employee = create_employee(api_client)
    kpi = create_kpi(api_client, employee["id"])

    fetched = api_client.get(f"/api/kpis/{kpi['id']}").json()
    assert fetched["name"] == "Hop dong ky moi"
    assert fetched["target_value"] == 100.0


def test_kpi_response_has_no_current_value_field(api_client):
    employee = create_employee(api_client)
    kpi = create_kpi(api_client, employee["id"])
    assert "current_value" not in kpi


def test_get_unknown_kpi_returns_404(api_client):
    assert api_client.get("/api/kpis/999999").status_code == 404


def test_patch_kpi_target(api_client):
    employee = create_employee(api_client)
    kpi = create_kpi(api_client, employee["id"])

    response = api_client.patch(f"/api/kpis/{kpi['id']}", json={"target_value": 150.0})

    assert response.status_code == 200
    assert response.json()["target_value"] == 150.0


def test_non_positive_target_is_rejected(api_client):
    employee = create_employee(api_client)
    response = api_client.post(
        "/api/kpis",
        json={
            "name": "Sai",
            "target_value": 0,
            "unit": "cai",
            "owner_id": employee["id"],
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    )
    assert response.status_code == 422


def test_period_end_before_start_is_rejected(api_client):
    employee = create_employee(api_client)
    response = api_client.post(
        "/api/kpis",
        json={
            "name": "Sai",
            "target_value": 10,
            "unit": "cai",
            "owner_id": employee["id"],
            "period_start": "2026-12-31",
            "period_end": "2026-01-01",
        },
    )
    assert response.status_code == 422


def test_create_and_patch_task(api_client):
    employee = create_employee(api_client)
    kpi = create_kpi(api_client, employee["id"])

    created = api_client.post(
        "/api/tasks",
        json={
            "title": "Chot hop dong khach X",
            "kpi_id": kpi["id"],
            "assignee_id": employee["id"],
        },
    )
    assert created.status_code == 201
    assert created.json()["status"] == "todo"

    patched = api_client.patch(
        f"/api/tasks/{created.json()['id']}", json={"status": "doing"}
    )
    assert patched.json()["status"] == "doing"


def test_task_with_unknown_kpi_returns_404(api_client):
    employee = create_employee(api_client)
    response = api_client.post(
        "/api/tasks",
        json={"title": "x", "kpi_id": 999999, "assignee_id": employee["id"]},
    )
    assert response.status_code == 404
```

- [ ] **Step 3: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_api_crud.py -v`
Expected: FAIL — mọi request trả 404 vì router chưa được gắn

- [ ] **Step 4: Viết `backend/app/schemas.py`**

```python
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


```

> Chỉ viết đúng các schema mà Task 11 dùng. Schema cho báo cáo, hàng đợi duyệt
> và dashboard được thêm vào chính file này ở Task 12, 13, 14 — mỗi task chỉ
> thêm phần nó thực sự dùng, để không có model nào nằm trong repo mà chưa có
> endpoint nào gọi tới.

- [ ] **Step 5: Tạo `backend/app/routers/__init__.py` rỗng, rồi viết ba router**

`backend/app/routers/employees.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Employee
from app.schemas import EmployeeCreate, EmployeeOut

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db)) -> list[Employee]:
    return list(db.scalars(select(Employee).order_by(Employee.id)).all())


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)) -> Employee:
    employee = Employee(name=payload.name, email=payload.email)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee
```

`backend/app/routers/kpis.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFoundError
from app.models import Employee, Kpi
from app.schemas import KpiCreate, KpiOut, KpiUpdate

router = APIRouter(prefix="/api/kpis", tags=["kpis"])


@router.get("", response_model=list[KpiOut])
def list_kpis(db: Session = Depends(get_db)) -> list[Kpi]:
    return list(db.scalars(select(Kpi).order_by(Kpi.id)).all())


@router.post("", response_model=KpiOut, status_code=status.HTTP_201_CREATED)
def create_kpi(payload: KpiCreate, db: Session = Depends(get_db)) -> Kpi:
    if db.get(Employee, payload.owner_id) is None:
        raise NotFoundError(f"Không tìm thấy nhân viên {payload.owner_id}")
    kpi = Kpi(**payload.model_dump())
    db.add(kpi)
    db.commit()
    db.refresh(kpi)
    return kpi


@router.get("/{kpi_id}", response_model=KpiOut)
def get_kpi(kpi_id: int, db: Session = Depends(get_db)) -> Kpi:
    kpi = db.get(Kpi, kpi_id)
    if kpi is None:
        raise NotFoundError(f"Không tìm thấy KPI {kpi_id}")
    return kpi


@router.patch("/{kpi_id}", response_model=KpiOut)
def update_kpi(
    kpi_id: int, payload: KpiUpdate, db: Session = Depends(get_db)
) -> Kpi:
    kpi = db.get(Kpi, kpi_id)
    if kpi is None:
        raise NotFoundError(f"Không tìm thấy KPI {kpi_id}")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(kpi, field, value)
    db.commit()
    db.refresh(kpi)
    return kpi
```

`backend/app/routers/tasks.py`:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotFoundError
from app.models import Employee, Kpi, Task
from app.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)) -> list[Task]:
    return list(db.scalars(select(Task).order_by(Task.id)).all())


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    if db.get(Kpi, payload.kpi_id) is None:
        raise NotFoundError(f"Không tìm thấy KPI {payload.kpi_id}")
    if db.get(Employee, payload.assignee_id) is None:
        raise NotFoundError(f"Không tìm thấy nhân viên {payload.assignee_id}")
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)
) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError(f"Không tìm thấy task {task_id}")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task
```

- [ ] **Step 6: Cập nhật `backend/app/main.py`**

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db import Base, engine
from app.errors import ConflictError, NotFoundError
from app.routers import employees, kpis, tasks


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Chỉ chạy khi server thật khởi động. Test ghi đè get_db sang SQLite
    # in-memory và không vào lifespan, nên không sinh file kpi.db thừa.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="KPI Weekly Report API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def handle_conflict(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(employees.router)
app.include_router(kpis.router)
app.include_router(tasks.router)
```

- [ ] **Step 7: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_api_crud.py tests/test_health.py -v`
Expected: PASS (10 test)

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas.py backend/app/routers backend/app/main.py backend/tests/conftest.py backend/tests/test_api_crud.py
git commit -m "feat(backend): router CRUD employee, KPI, task va exception handler"
```

---

### Task 12: Router báo cáo (nộp, xem, trích lại)

**Files:**
- Create: `backend/app/routers/reports.py`, `backend/app/dependencies.py`
- Modify: `backend/app/schemas.py` (thêm schema báo cáo ở cuối file)
- Modify: `backend/app/main.py` (gắn thêm router `reports`)
- Test: `backend/tests/test_api_reports.py`

**Interfaces:**
- Consumes: `app.services.extraction.submit_report`, `reextract_report`, `app.llm.factory.get_provider`, `app.config.get_settings`
- Produces: `app.dependencies.get_llm_provider() -> LlmProvider` (dependency FastAPI, ghi đè được trong test); router `app.routers.reports.router`

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_api_reports.py`:

```python
import pytest


@pytest.fixture
def seeded(api_client):
    employee = api_client.post(
        "/api/employees", json={"name": "Nguyen Van A", "email": "a@example.com"}
    ).json()
    kpi = api_client.post(
        "/api/kpis",
        json={
            "name": "Hop dong ky moi",
            "target_value": 100.0,
            "unit": "hop dong",
            "owner_id": employee["id"],
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    ).json()
    task = api_client.post(
        "/api/tasks",
        json={
            "title": "Chot hop dong khach X",
            "kpi_id": kpi["id"],
            "assignee_id": employee["id"],
        },
    ).json()
    return {"employee": employee, "kpi": kpi, "task": task}


def submit(api_client, employee_id, text="Ky them 5 hop dong ky moi."):
    return api_client.post(
        "/api/reports",
        json={"employee_id": employee_id, "week_start": "2026-03-02", "raw_text": text},
    )


def test_submitting_report_returns_suggestions(api_client, seeded):
    response = submit(api_client, seeded["employee"]["id"])

    assert response.status_code == 201
    body = response.json()
    assert body["extraction_status"] == "extracted"
    assert body["provider_name"] == "mock"
    assert len(body["kpi_suggestions"]) == 1
    assert body["kpi_suggestions"][0]["suggested_delta"] == 5.0
    assert body["kpi_suggestions"][0]["status"] == "pending"


def test_duplicate_submission_returns_409(api_client, seeded):
    submit(api_client, seeded["employee"]["id"])

    second = submit(api_client, seeded["employee"]["id"], text="lan hai")

    assert second.status_code == 409
    assert len(api_client.get("/api/reports").json()) == 1


def test_get_report_by_id(api_client, seeded):
    created = submit(api_client, seeded["employee"]["id"]).json()

    fetched = api_client.get(f"/api/reports/{created['id']}").json()

    assert fetched["id"] == created["id"]
    assert fetched["raw_text"] == "Ky them 5 hop dong ky moi."


def test_get_unknown_report_returns_404(api_client):
    assert api_client.get("/api/reports/999999").status_code == 404


def test_reextract_replaces_pending_suggestions(api_client, seeded):
    created = submit(api_client, seeded["employee"]["id"]).json()
    old_id = created["kpi_suggestions"][0]["id"]

    response = api_client.post(f"/api/reports/{created['id']}/extract")

    assert response.status_code == 200
    new_id = response.json()["kpi_suggestions"][0]["id"]
    assert new_id != old_id


def test_failed_extraction_is_reported(api_client, seeded):
    """Nhân viên không có KPI/Task nào -> mock không trích được gì, nhưng vẫn
    là một lần trích xuất thành công với danh sách rỗng."""
    other = api_client.post(
        "/api/employees", json={"name": "Tran Thi B", "email": "b@example.com"}
    ).json()

    body = submit(api_client, other["id"], text="Tuan nay hop giao ban.").json()

    assert body["extraction_status"] == "extracted"
    assert body["kpi_suggestions"] == []
    assert body["blockers"] == []
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_api_reports.py -v`
Expected: FAIL — `POST /api/reports` trả 404 vì router chưa tồn tại

- [ ] **Step 3: Thêm schema báo cáo vào cuối `backend/app/schemas.py`**

Bổ sung `SuggestionStatus` vào dòng `from app.models import ...`, rồi thêm:

```python
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
```

`extraction_status` và `status` khai báo bằng kiểu enum chứ không phải `str`, để
Pydantic luôn serialize ra giá trị (`"extracted"`, `"pending"`) một cách xác định.
Nhớ thêm cả `ExtractionStatus` vào dòng import từ `app.models`.

- [ ] **Step 4: Viết `backend/app/dependencies.py`**

```python
"""Dependency dùng chung. Tách riêng để test ghi đè được provider."""

from app.config import get_settings
from app.llm.base import LlmProvider
from app.llm.factory import get_provider


def get_llm_provider() -> LlmProvider:
    return get_provider(get_settings())
```

- [ ] **Step 5: Viết `backend/app/routers/reports.py`**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_llm_provider
from app.errors import NotFoundError
from app.llm.base import LlmProvider
from app.models import Employee, WeeklyReport
from app.schemas import ReportCreate, ReportOut
from app.services.extraction import reextract_report, submit_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db)) -> list[WeeklyReport]:
    return list(
        db.scalars(select(WeeklyReport).order_by(WeeklyReport.id.desc())).all()
    )


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    provider: LlmProvider = Depends(get_llm_provider),
) -> WeeklyReport:
    if db.get(Employee, payload.employee_id) is None:
        raise NotFoundError(f"Không tìm thấy nhân viên {payload.employee_id}")
    return submit_report(
        db,
        employee_id=payload.employee_id,
        week_start=payload.week_start,
        raw_text=payload.raw_text,
        provider=provider,
    )


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)) -> WeeklyReport:
    report = db.get(WeeklyReport, report_id)
    if report is None:
        raise NotFoundError(f"Không tìm thấy báo cáo {report_id}")
    return report


@router.post("/{report_id}/extract", response_model=ReportOut)
def reextract(
    report_id: int,
    db: Session = Depends(get_db),
    provider: LlmProvider = Depends(get_llm_provider),
) -> WeeklyReport:
    report = db.get(WeeklyReport, report_id)
    if report is None:
        raise NotFoundError(f"Không tìm thấy báo cáo {report_id}")
    return reextract_report(db, report, provider)
```

- [ ] **Step 6: Gắn router vào `backend/app/main.py`**

Thêm `reports` vào dòng import và thêm `app.include_router(reports.router)` ở cuối file:

```python
from app.routers import employees, kpis, reports, tasks
...
app.include_router(reports.router)
```

- [ ] **Step 7: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_api_reports.py -v`
Expected: PASS (6 test)

- [ ] **Step 8: Commit**

```bash
git add backend/app/dependencies.py backend/app/routers/reports.py backend/app/main.py backend/tests/test_api_reports.py
git commit -m "feat(backend): router nop bao cao, xem va trich lai"
```

---

### Task 13: Router duyệt đề xuất

**Files:**
- Create: `backend/app/routers/suggestions.py`
- Modify: `backend/app/schemas.py` (thêm schema hàng đợi duyệt ở cuối file)
- Modify: `backend/app/main.py` (gắn router `suggestions`)
- Test: `backend/tests/test_api_suggestions.py`, `backend/tests/test_api_reports.py` (thêm một test ở cuối)

**Interfaces:**
- Consumes: `app.services.approval.*`, `app.schemas.SuggestionQueueOut`, `SuggestionContextOut`, `KpiApproveIn`, `TaskApproveIn`
- Produces: router `app.routers.suggestions.router`

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_api_suggestions.py`:

```python
import pytest


@pytest.fixture
def submitted(api_client):
    employee = api_client.post(
        "/api/employees", json={"name": "Nguyen Van A", "email": "a@example.com"}
    ).json()
    kpi = api_client.post(
        "/api/kpis",
        json={
            "name": "Hop dong ky moi",
            "target_value": 100.0,
            "unit": "hop dong",
            "owner_id": employee["id"],
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
        },
    ).json()
    task = api_client.post(
        "/api/tasks",
        json={
            "title": "Chot hop dong khach X",
            "kpi_id": kpi["id"],
            "assignee_id": employee["id"],
        },
    ).json()
    report = api_client.post(
        "/api/reports",
        json={
            "employee_id": employee["id"],
            "week_start": "2026-03-02",
            "raw_text": "Ky them 5 hop dong ky moi.\nDa chot hop dong khach X.",
        },
    ).json()
    return {"employee": employee, "kpi": kpi, "task": task, "report": report}


def test_queue_returns_two_separate_lists(api_client, submitted):
    body = api_client.get("/api/suggestions?status=pending").json()

    assert len(body["kpi_updates"]) == 1
    assert len(body["task_completions"]) == 1
    assert body["kpi_updates"][0]["employee_name"] == "Nguyen Van A"
    assert body["kpi_updates"][0]["week_start"] == "2026-03-02"


def test_approving_kpi_suggestion(api_client, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]

    response = api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        json={"final_kpi_id": submitted["kpi"]["id"], "final_delta": 5.0},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["final_delta"] == 5.0


def test_approving_with_edited_delta(api_client, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]

    body = api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        json={
            "final_kpi_id": submitted["kpi"]["id"],
            "final_delta": 3.0,
            "note": "khach huy 2",
        },
    ).json()

    assert body["suggested_delta"] == 5.0
    assert body["final_delta"] == 3.0
    assert body["review_note"] == "khach huy 2"


def test_double_approval_returns_409(api_client, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]
    payload = {"final_kpi_id": submitted["kpi"]["id"], "final_delta": 5.0}
    api_client.post(f"/api/suggestions/kpi/{suggestion['id']}/approve", json=payload)

    second = api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve", json=payload
    )

    assert second.status_code == 409


def test_rejecting_kpi_suggestion(api_client, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]

    response = api_client.post(f"/api/suggestions/kpi/{suggestion['id']}/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_approved_suggestion_leaves_queue(api_client, submitted):
    suggestion = submitted["report"]["kpi_suggestions"][0]
    api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        json={"final_kpi_id": submitted["kpi"]["id"], "final_delta": 5.0},
    )

    body = api_client.get("/api/suggestions?status=pending").json()

    assert body["kpi_updates"] == []
    assert len(body["task_completions"]) == 1


def test_approving_task_suggestion_marks_task_done(api_client, submitted):
    suggestion = submitted["report"]["task_suggestions"][0]

    response = api_client.post(
        f"/api/suggestions/task/{suggestion['id']}/approve",
        json={"final_task_id": submitted["task"]["id"]},
    )

    assert response.status_code == 200
    tasks = api_client.get("/api/tasks").json()
    assert tasks[0]["status"] == "done"


def test_rejecting_task_suggestion_leaves_task_todo(api_client, submitted):
    suggestion = submitted["report"]["task_suggestions"][0]

    api_client.post(f"/api/suggestions/task/{suggestion['id']}/reject")

    tasks = api_client.get("/api/tasks").json()
    assert tasks[0]["status"] == "todo"


def test_unknown_suggestion_returns_404(api_client, submitted):
    assert api_client.post("/api/suggestions/kpi/999999/reject").status_code == 404
```

Và thêm vào **cuối** `backend/tests/test_api_reports.py` (file của Task 12) test
khoá trích lại — nó cần endpoint duyệt nên chỉ chạy được từ task này:

```python
def test_reextract_blocked_after_approval_returns_409(api_client, seeded):
    created = submit(api_client, seeded["employee"]["id"]).json()
    suggestion = created["kpi_suggestions"][0]
    approved = api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        json={"final_kpi_id": seeded["kpi"]["id"], "final_delta": 5.0},
    )
    assert approved.status_code == 200

    response = api_client.post(f"/api/reports/{created['id']}/extract")

    assert response.status_code == 409
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_api_suggestions.py -v`
Expected: FAIL — endpoint trả 404 vì router chưa tồn tại

- [ ] **Step 3: Thêm schema hàng đợi duyệt vào cuối `backend/app/schemas.py`**

```python
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
```

- [ ] **Step 4: Viết `backend/app/routers/suggestions.py`**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    KpiUpdateSuggestion,
    SuggestionStatus,
    TaskCompletionSuggestion,
)
from app.schemas import (
    KpiApproveIn,
    KpiSuggestionOut,
    SuggestionContextOut,
    SuggestionQueueOut,
    TaskApproveIn,
    TaskSuggestionOut,
)
from app.services.approval import (
    approve_kpi_suggestion,
    approve_task_suggestion,
    reject_kpi_suggestion,
    reject_task_suggestion,
)

router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])


@router.get("", response_model=SuggestionQueueOut)
def list_suggestions(
    status: SuggestionStatus = Query(default=SuggestionStatus.PENDING),
    db: Session = Depends(get_db),
) -> SuggestionQueueOut:
    kpi_rows = db.scalars(
        select(KpiUpdateSuggestion)
        .where(KpiUpdateSuggestion.status == status)
        .order_by(KpiUpdateSuggestion.id)
    ).all()
    task_rows = db.scalars(
        select(TaskCompletionSuggestion)
        .where(TaskCompletionSuggestion.status == status)
        .order_by(TaskCompletionSuggestion.id)
    ).all()

    return SuggestionQueueOut(
        kpi_updates=[
            SuggestionContextOut(
                id=row.id,
                report_id=row.report_id,
                employee_name=row.report.employee.name,
                week_start=row.report.week_start,
                suggested_kpi_id=row.suggested_kpi_id,
                suggested_delta=row.suggested_delta,
                evidence=row.evidence,
            )
            for row in kpi_rows
        ],
        task_completions=[
            SuggestionContextOut(
                id=row.id,
                report_id=row.report_id,
                employee_name=row.report.employee.name,
                week_start=row.report.week_start,
                suggested_task_id=row.suggested_task_id,
                raw_text=row.raw_text,
            )
            for row in task_rows
        ],
    )


@router.post("/kpi/{suggestion_id}/approve", response_model=KpiSuggestionOut)
def approve_kpi(
    suggestion_id: int, payload: KpiApproveIn, db: Session = Depends(get_db)
) -> KpiUpdateSuggestion:
    return approve_kpi_suggestion(
        db,
        suggestion_id=suggestion_id,
        final_kpi_id=payload.final_kpi_id,
        final_delta=payload.final_delta,
        note=payload.note,
    )


@router.post("/kpi/{suggestion_id}/reject", response_model=KpiSuggestionOut)
def reject_kpi(
    suggestion_id: int, db: Session = Depends(get_db)
) -> KpiUpdateSuggestion:
    return reject_kpi_suggestion(db, suggestion_id=suggestion_id)


@router.post("/task/{suggestion_id}/approve", response_model=TaskSuggestionOut)
def approve_task(
    suggestion_id: int, payload: TaskApproveIn, db: Session = Depends(get_db)
) -> TaskCompletionSuggestion:
    return approve_task_suggestion(
        db, suggestion_id=suggestion_id, final_task_id=payload.final_task_id
    )


@router.post("/task/{suggestion_id}/reject", response_model=TaskSuggestionOut)
def reject_task(
    suggestion_id: int, db: Session = Depends(get_db)
) -> TaskCompletionSuggestion:
    return reject_task_suggestion(db, suggestion_id=suggestion_id)
```

- [ ] **Step 5: Gắn router vào `backend/app/main.py`**

```python
from app.routers import employees, kpis, reports, suggestions, tasks
...
app.include_router(suggestions.router)
```

- [ ] **Step 6: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_api_suggestions.py tests/test_api_reports.py -v`
Expected: PASS (10 test trong test_api_suggestions.py + 7 test trong test_api_reports.py)

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/suggestions.py backend/app/schemas.py backend/app/main.py backend/tests/test_api_suggestions.py backend/tests/test_api_reports.py
git commit -m "feat(backend): router hang doi duyet de xuat KPI va task"
```

---

### Task 14: Router dashboard và test trọn vòng

**Files:**
- Create: `backend/app/routers/dashboard.py`, `backend/README.md`
- Modify: `backend/app/schemas.py` (thêm schema dashboard ở cuối file)
- Modify: `backend/app/main.py` (gắn router `dashboard`)
- Test: `backend/tests/test_api_dashboard.py`, `backend/tests/test_end_to_end.py`

**Interfaces:**
- Consumes: `app.services.dashboard.build_dashboard`, `app.schemas.DashboardItemOut`
- Produces: router `app.routers.dashboard.router`

- [ ] **Step 1: Viết test thất bại**

`backend/tests/test_api_dashboard.py`:

```python
from datetime import date, timedelta

import pytest

TODAY = date.today()
PERIOD_START = TODAY - timedelta(days=50)
PERIOD_END = TODAY + timedelta(days=50)


@pytest.fixture
def kpi(api_client):
    employee = api_client.post(
        "/api/employees", json={"name": "Nguyen Van A", "email": "a@example.com"}
    ).json()
    return api_client.post(
        "/api/kpis",
        json={
            "name": "Hop dong ky moi",
            "target_value": 100.0,
            "unit": "hop dong",
            "owner_id": employee["id"],
            "period_start": PERIOD_START.isoformat(),
            "period_end": PERIOD_END.isoformat(),
        },
    ).json()


def test_dashboard_lists_kpi_with_zero_progress(api_client, kpi):
    body = api_client.get("/api/dashboard").json()

    assert len(body) == 1
    item = body[0]
    assert item["kpi_id"] == kpi["id"]
    assert item["actual_value"] == 0.0
    assert item["target_value"] == 100.0
    assert item["owner_name"] == "Nguyen Van A"


def test_dashboard_flags_at_risk_when_far_behind(api_client, kpi):
    item = api_client.get("/api/dashboard").json()[0]

    # đã qua ~50% kỳ, kỳ vọng ~50, thực tế 0 -> dưới 80% kỳ vọng
    assert item["at_risk"] is True
    assert item["status"] == "at_risk"


def test_dashboard_is_empty_without_kpis(api_client):
    assert api_client.get("/api/dashboard").json() == []
```

`backend/tests/test_end_to_end.py`:

```python
from datetime import date, timedelta

TODAY = date.today()
PERIOD_START = TODAY - timedelta(days=50)
PERIOD_END = TODAY + timedelta(days=50)


def test_full_cycle_from_kpi_to_dashboard(api_client):
    """Tạo KPI -> nộp báo cáo -> duyệt -> dashboard đổi số và tắt cảnh báo."""
    employee = api_client.post(
        "/api/employees", json={"name": "Nguyen Van A", "email": "a@example.com"}
    ).json()
    kpi = api_client.post(
        "/api/kpis",
        json={
            "name": "Hop dong ky moi",
            "target_value": 100.0,
            "unit": "hop dong",
            "owner_id": employee["id"],
            "period_start": PERIOD_START.isoformat(),
            "period_end": PERIOD_END.isoformat(),
        },
    ).json()

    before = api_client.get("/api/dashboard").json()[0]
    assert before["actual_value"] == 0.0
    assert before["at_risk"] is True

    report = api_client.post(
        "/api/reports",
        json={
            "employee_id": employee["id"],
            "week_start": "2026-03-02",
            "raw_text": "Tuan nay ky them 60 hop dong ky moi.",
        },
    ).json()
    assert report["extraction_status"] == "extracted"
    suggestion = report["kpi_suggestions"][0]
    assert suggestion["suggested_delta"] == 60.0

    queue = api_client.get("/api/suggestions?status=pending").json()
    assert len(queue["kpi_updates"]) == 1

    approved = api_client.post(
        f"/api/suggestions/kpi/{suggestion['id']}/approve",
        json={"final_kpi_id": kpi["id"], "final_delta": 60.0},
    )
    assert approved.status_code == 200

    after = api_client.get("/api/dashboard").json()[0]
    assert after["actual_value"] == 60.0
    assert after["at_risk"] is False
    assert after["status"] == "on_track"

    assert api_client.get("/api/suggestions?status=pending").json()["kpi_updates"] == []
```

- [ ] **Step 2: Chạy test để xác nhận nó thất bại**

Run: `pytest tests/test_api_dashboard.py tests/test_end_to_end.py -v`
Expected: FAIL — `GET /api/dashboard` trả 404

- [ ] **Step 3: Thêm schema dashboard vào cuối `backend/app/schemas.py`**

```python
class DashboardItemOut(BaseModel):
    kpi_id: int
    kpi_name: str
    unit: str
    owner_name: str
    period_start: date
    period_end: date
    actual_value: float
    target_value: float
    expected_value: float
    percent_complete: float
    status: str
    at_risk: bool
```

- [ ] **Step 4: Viết `backend/app/routers/dashboard.py`**

```python
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import DashboardItemOut
from app.services.dashboard import build_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=list[DashboardItemOut])
def get_dashboard(db: Session = Depends(get_db)) -> list[DashboardItemOut]:
    # "Hôm nay" chỉ được đọc ở biên HTTP; service và rules luôn nhận nó qua tham số.
    items = build_dashboard(db, today=date.today())
    return [
        DashboardItemOut(
            kpi_id=item.kpi_id,
            kpi_name=item.kpi_name,
            unit=item.unit,
            owner_name=item.owner_name,
            period_start=item.period_start,
            period_end=item.period_end,
            actual_value=item.evaluation.actual_value,
            target_value=item.evaluation.target_value,
            expected_value=item.evaluation.expected_value,
            percent_complete=item.evaluation.percent_complete,
            status=item.evaluation.status.value,
            at_risk=item.evaluation.at_risk,
        )
        for item in items
    ]
```

- [ ] **Step 5: Gắn router vào `backend/app/main.py`**

```python
from app.routers import dashboard, employees, kpis, reports, suggestions, tasks
...
app.include_router(dashboard.router)
```

- [ ] **Step 6: Chạy test để xác nhận nó pass**

Run: `pytest tests/test_api_dashboard.py tests/test_end_to_end.py -v`
Expected: PASS (4 test)

- [ ] **Step 7: Chạy toàn bộ bộ test**

Run: `pytest -v`
Expected: PASS toàn bộ, không có test nào bị skip

- [ ] **Step 8: Viết `backend/README.md`**

```markdown
# Backend — API báo cáo tuần & KPI

## Chạy lần đầu

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

## Chạy server

```powershell
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Chạy test

```powershell
pytest
```

Test luôn dùng `MockProvider` và SQLite in-memory — **không gọi mạng**.

## Dùng Claude thật

Sửa `.env`:

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Mặc định là `mock`. Model mặc định là `claude-sonnet-5`.

## Thiết kế

Xem `docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md`.
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/routers/dashboard.py backend/app/schemas.py backend/app/main.py backend/README.md backend/tests/test_api_dashboard.py backend/tests/test_end_to_end.py
git commit -m "feat(backend): router dashboard, test tron vong va huong dan chay"
```

---

## Kết thúc Giai đoạn 1

Sau Task 14, backend đã hoàn chỉnh và tự đứng được: `pytest` xanh toàn bộ, `uvicorn app.main:app` chạy được, `/docs` liệt kê đủ endpoint.

**Dừng lại ở đây để người dùng merge vào `main`.** Không bắt đầu Giai đoạn 2.

## Giai đoạn 2 — Frontend (làm sau, có plan riêng)

Nằm ngoài phạm vi kế hoạch này. Sau khi Giai đoạn 1 được merge, viết một plan riêng cho frontend React + Vite + TypeScript với bốn trang đã mô tả ở mục 10 của spec: Thiết lập, Nộp báo cáo, Hàng đợi duyệt, Dashboard. Backend đã sẵn sàng phục vụ: CORS đã mở cho `http://localhost:5173`, và mọi endpoint frontend cần đều đã có.
