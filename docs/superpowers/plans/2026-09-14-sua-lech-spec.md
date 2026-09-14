# Sửa 4 chỗ code lệch spec + đồng bộ spec theo code — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Đưa code về đúng spec ở 4 điểm lệch, đưa spec về đúng code ở 7 điểm code chặt hơn spec, và ghi lại một hạn chế đã biết — kết thúc bằng một Pull Request trên GitHub.

**Architecture:** Ba module service mới (`employee`, `kpi`, `task`) nhận toàn bộ quyết định nghiệp vụ và ranh giới giao dịch từ ba router tương ứng, theo đúng idiom của `services/approval.py` đang có. Router chỉ còn dịch HTTP ↔ service. Hai `CheckConstraint` đưa ràng buộc KPI của spec §5 xuống tầng DB. Phía frontend thêm `getKpi` và `tsconfig.node.json` cho khớp bố cục spec. **Hành vi HTTP không đổi một ly** — mọi mã lỗi, thông điệp và response body giữ nguyên; 129 test backend hiện có là lưới an toàn.

**Tech Stack:** FastAPI, SQLAlchemy 2.x (`Mapped` / `mapped_column`), Pydantic v2, pytest; React 18 + Vite 5 + TypeScript 5 + Vitest 2; Playwright cho e2e.

**Spec:**
- `docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md` (backend — §4, §5, §7.4, §8, §9, §12)
- `docs/superpowers/specs/2026-09-11-frontend-giai-doan-2-design.md` (frontend — §5, §6)
- `docs/diagrams/*.md` (bốn sơ đồ đã chỉ ra từng chỗ lệch; hiện chưa được commit)

## Global Constraints

- **Hành vi HTTP không đổi.** Mọi endpoint giữ nguyên mã trạng thái, thông điệp lỗi (kể cả nguyên văn tiếng Việt) và response model. Không endpoint nào được thêm, đổi hay bỏ.
- **Baseline phải xanh suốt.** 129 test backend và 25 test Vitest hiện có phải pass ở **mọi** commit. Test mới được phép thêm vào, không được sửa hay xoá test cũ.
- **Không đụng tới `routers/reports.py`.** Nó cũng tự kiểm `db.get(Employee, ...)` — đã quyết định để nguyên và chỉ ghi vào spec, không refactor trong PR này.
- **Không thêm dependency mới** ở cả backend lẫn frontend.
- Comment và thông điệp lỗi viết **tiếng Việt**, theo đúng giọng của code đang có.
- Mọi lệnh chạy từ Windows PowerShell; virtualenv ở gốc repo: `D:\projects\task-and-kpi\.venv\Scripts\python.exe`.
- Làm trong **git worktree** riêng, nhánh `fix/spec-drift-services`. Không merge vào `main` ở local — kết thúc bằng Pull Request.

---

### Task 1: `services/employee.py` — tách nghiệp vụ khỏi `routers/employees.py`

**Files:**
- Create: `backend/app/services/employee.py`
- Modify: `backend/app/routers/employees.py` (viết lại toàn bộ, 29 dòng)
- Test: `backend/tests/test_service_employee.py` (tạo mới)

**Interfaces:**
- Consumes: `app.errors.ConflictError`, `app.models.Employee` (đã có).
- Produces:
  - `list_employees(db: Session) -> list[Employee]`
  - `create_employee(db: Session, *, name: str, email: str) -> Employee`

- [ ] **Step 1: Viết test thất bại cho service**

Tạo `backend/tests/test_service_employee.py`:

```python
import pytest

from app.errors import ConflictError
from app.models import Employee
from app.services import employee as employee_service


def test_create_employee_persists_and_returns_row(db_session):
    created = employee_service.create_employee(
        db_session, name="Nguyen Van A", email="a@example.com"
    )

    assert created.id is not None
    assert db_session.get(Employee, created.id).email == "a@example.com"


def test_create_employee_with_duplicate_email_raises_conflict(db_session):
    employee_service.create_employee(
        db_session, name="Nguoi thu nhat", email="a@example.com"
    )

    with pytest.raises(ConflictError):
        employee_service.create_employee(
            db_session, name="Nguoi thu hai", email="a@example.com"
        )

    assert len(employee_service.list_employees(db_session)) == 1


def test_list_employees_is_ordered_by_id(db_session):
    first = employee_service.create_employee(db_session, name="A", email="a@example.com")
    second = employee_service.create_employee(db_session, name="B", email="b@example.com")

    assert [row.id for row in employee_service.list_employees(db_session)] == [
        first.id,
        second.id,
    ]
```

- [ ] **Step 2: Chạy test, xác nhận nó fail**

```powershell
cd D:\projects\task-and-kpi\backend
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest tests/test_service_employee.py -q
```

Kỳ vọng: FAIL với `ModuleNotFoundError: No module named 'app.services.employee'`.

- [ ] **Step 3: Viết `backend/app/services/employee.py`**

```python
"""Nghiệp vụ nhân viên. Router chỉ dịch HTTP; mọi quyết định nghiệp vụ và
ranh giới giao dịch nằm ở đây.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ConflictError
from app.models import Employee


def list_employees(db: Session) -> list[Employee]:
    return list(db.scalars(select(Employee).order_by(Employee.id)).all())


def create_employee(db: Session, *, name: str, email: str) -> Employee:
    # Email là UNIQUE ở tầng DB. Kiểm trước để trả 409 thay vì để IntegrityError
    # thoát ra thành 500. Đây là check-then-insert: hai request đồng thời vẫn
    # lọt qua cả hai lần SELECT — xem "Hạn chế đã biết" trong README.
    if db.scalar(select(Employee).where(Employee.email == email)) is not None:
        raise ConflictError(f"Email {email} đã được dùng")

    employee = Employee(name=name, email=email)
    try:
        db.add(employee)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(employee)
    return employee
```

- [ ] **Step 4: Chạy lại test service, xác nhận pass**

```powershell
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest tests/test_service_employee.py -q
```

Kỳ vọng: `3 passed`.

- [ ] **Step 5: Viết lại `backend/app/routers/employees.py` cho mỏng**

Thay **toàn bộ** nội dung file bằng:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Employee
from app.schemas import EmployeeCreate, EmployeeOut
from app.services import employee as employee_service

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db)) -> list[Employee]:
    return employee_service.list_employees(db)


@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)) -> Employee:
    return employee_service.create_employee(db, **payload.model_dump())
```

Router giờ không còn `select`, `db.add`, `db.commit` hay `ConflictError` — đúng spec §4.

- [ ] **Step 6: Chạy toàn bộ test backend**

```powershell
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest -q
```

Kỳ vọng: `132 passed` (129 cũ + 3 mới). Đặc biệt `tests/test_api_crud.py::test_duplicate_email_returns_409` phải vẫn pass.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/employee.py backend/app/routers/employees.py backend/tests/test_service_employee.py
git commit -m "refactor(employees): tach nghiep vu sang services/employee.py"
```

---

### Task 2: `services/kpi.py` — tách nghiệp vụ khỏi `routers/kpis.py`

**Files:**
- Create: `backend/app/services/kpi.py`
- Modify: `backend/app/routers/kpis.py` (viết lại toàn bộ, 62 dòng)
- Test: `backend/tests/test_service_kpi.py` (tạo mới)

**Interfaces:**
- Consumes: `app.errors.NotFoundError`, `app.errors.InvalidInputError`, `app.models.Employee`, `app.models.Kpi`.
- Produces:
  - `list_kpis(db: Session) -> list[Kpi]`
  - `get_kpi(db: Session, kpi_id: int) -> Kpi`
  - `create_kpi(db: Session, *, name: str, target_value: float, unit: str, owner_id: int, period_start: date, period_end: date) -> Kpi`
  - `update_kpi(db: Session, kpi_id: int, changes: dict[str, Any]) -> Kpi`

Lưu ý ranh giới: `changes` là một dict **đã lọc** do router dựng từ `payload.model_dump(exclude_unset=True, exclude_none=True)`. Việc "gửi `null` tường minh coi như không gửi" là quy ước **định dạng PATCH trên dây**, không phải quyết định nghiệp vụ, nên nó ở lại router.

- [ ] **Step 1: Viết test thất bại cho service**

Tạo `backend/tests/test_service_kpi.py`:

```python
from datetime import date

import pytest

from app.errors import InvalidInputError, NotFoundError
from app.services import employee as employee_service
from app.services import kpi as kpi_service


def make_owner(db_session, email="owner@example.com"):
    return employee_service.create_employee(db_session, name="Chu KPI", email=email)


def make_kpi(db_session, owner_id, **overrides):
    fields = {
        "name": "Hop dong ky moi",
        "target_value": 100.0,
        "unit": "hop dong",
        "owner_id": owner_id,
        "period_start": date(2026, 1, 1),
        "period_end": date(2026, 12, 31),
    }
    fields.update(overrides)
    return kpi_service.create_kpi(db_session, **fields)


def test_create_kpi_persists_row(db_session):
    owner = make_owner(db_session)
    created = make_kpi(db_session, owner.id)

    assert created.id is not None
    assert kpi_service.get_kpi(db_session, created.id).target_value == 100.0


def test_create_kpi_with_unknown_owner_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        make_kpi(db_session, 999999)


def test_get_unknown_kpi_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        kpi_service.get_kpi(db_session, 999999)


def test_update_kpi_applies_changes(db_session):
    owner = make_owner(db_session)
    kpi = make_kpi(db_session, owner.id)

    updated = kpi_service.update_kpi(db_session, kpi.id, {"target_value": 150.0})

    assert updated.target_value == 150.0


def test_update_kpi_rejects_inverted_period_and_keeps_stored_value(db_session):
    """PATCH chỉ đổi một mốc vẫn phải bị chặn nếu tạo ra kỳ ngược, và giá trị
    đang lưu phải nguyên vẹn sau khi service rollback."""
    owner = make_owner(db_session)
    kpi = make_kpi(db_session, owner.id)

    with pytest.raises(InvalidInputError):
        kpi_service.update_kpi(db_session, kpi.id, {"period_end": date(2025, 1, 1)})

    assert kpi_service.get_kpi(db_session, kpi.id).period_end == date(2026, 12, 31)


def test_update_unknown_kpi_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        kpi_service.update_kpi(db_session, 999999, {"target_value": 5.0})


def test_list_kpis_is_ordered_by_id(db_session):
    owner = make_owner(db_session)
    first = make_kpi(db_session, owner.id, name="KPI 1")
    second = make_kpi(db_session, owner.id, name="KPI 2")

    assert [row.id for row in kpi_service.list_kpis(db_session)] == [
        first.id,
        second.id,
    ]
```

- [ ] **Step 2: Chạy test, xác nhận nó fail**

```powershell
cd D:\projects\task-and-kpi\backend
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest tests/test_service_kpi.py -q
```

Kỳ vọng: FAIL với `ModuleNotFoundError: No module named 'app.services.kpi'`.

- [ ] **Step 3: Viết `backend/app/services/kpi.py`**

```python
"""Nghiệp vụ KPI. Router chỉ dịch HTTP; mọi quyết định nghiệp vụ và ranh giới
giao dịch nằm ở đây.
"""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidInputError, NotFoundError
from app.models import Employee, Kpi


def list_kpis(db: Session) -> list[Kpi]:
    return list(db.scalars(select(Kpi).order_by(Kpi.id)).all())


def get_kpi(db: Session, kpi_id: int) -> Kpi:
    kpi = db.get(Kpi, kpi_id)
    if kpi is None:
        raise NotFoundError(f"Không tìm thấy KPI {kpi_id}")
    return kpi


def create_kpi(
    db: Session,
    *,
    name: str,
    target_value: float,
    unit: str,
    owner_id: int,
    period_start: date,
    period_end: date,
) -> Kpi:
    if db.get(Employee, owner_id) is None:
        raise NotFoundError(f"Không tìm thấy nhân viên {owner_id}")

    kpi = Kpi(
        name=name,
        target_value=target_value,
        unit=unit,
        owner_id=owner_id,
        period_start=period_start,
        period_end=period_end,
    )
    try:
        db.add(kpi)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(kpi)
    return kpi


def update_kpi(db: Session, kpi_id: int, changes: dict[str, Any]) -> Kpi:
    kpi = get_kpi(db, kpi_id)

    for field, value in changes.items():
        setattr(kpi, field, value)

    # Kiểm sau khi đã trộn với giá trị đang lưu: PATCH chỉ đổi một trong hai
    # mốc thời gian vẫn có thể tạo ra kỳ ngược. Kỳ ngược khiến
    # compute_elapsed_ratio coi như kỳ dài 0 ngày và trả 1.0, làm KPI bị
    # cảnh báo "có nguy cơ" oan. rollback() vứt bỏ các setattr ở trên.
    if kpi.period_end < kpi.period_start:
        db.rollback()
        raise InvalidInputError("period_end phải không nhỏ hơn period_start")

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(kpi)
    return kpi
```

- [ ] **Step 4: Chạy lại test service, xác nhận pass**

```powershell
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest tests/test_service_kpi.py -q
```

Kỳ vọng: `7 passed`.

- [ ] **Step 5: Viết lại `backend/app/routers/kpis.py` cho mỏng**

Thay **toàn bộ** nội dung file bằng:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Kpi
from app.schemas import KpiCreate, KpiOut, KpiUpdate
from app.services import kpi as kpi_service

router = APIRouter(prefix="/api/kpis", tags=["kpis"])


@router.get("", response_model=list[KpiOut])
def list_kpis(db: Session = Depends(get_db)) -> list[Kpi]:
    return kpi_service.list_kpis(db)


@router.post("", response_model=KpiOut, status_code=status.HTTP_201_CREATED)
def create_kpi(payload: KpiCreate, db: Session = Depends(get_db)) -> Kpi:
    return kpi_service.create_kpi(db, **payload.model_dump())


@router.get("/{kpi_id}", response_model=KpiOut)
def get_kpi(kpi_id: int, db: Session = Depends(get_db)) -> Kpi:
    return kpi_service.get_kpi(db, kpi_id)


@router.patch("/{kpi_id}", response_model=KpiOut)
def update_kpi(
    kpi_id: int, payload: KpiUpdate, db: Session = Depends(get_db)
) -> Kpi:
    # exclude_none: PATCH là cập nhật một phần, không trường nào ở đây được
    # phép thành null. Gửi null tường minh coi như không gửi — đó là quy ước
    # định dạng trên dây, nên nó ở lại biên HTTP.
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    return kpi_service.update_kpi(db, kpi_id, changes)
```

- [ ] **Step 6: Chạy toàn bộ test backend**

```powershell
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest -q
```

Kỳ vọng: `139 passed` (132 + 7 mới). Bốn test dễ vỡ nhất phải xanh:
`test_patch_cannot_create_inverted_period`, `test_patch_with_explicit_null_is_ignored`,
`test_get_unknown_kpi_returns_404`, `test_patch_kpi_target`.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/kpi.py backend/app/routers/kpis.py backend/tests/test_service_kpi.py
git commit -m "refactor(kpis): tach nghiep vu sang services/kpi.py"
```

---

### Task 3: `services/task.py` — tách nghiệp vụ khỏi `routers/tasks.py`

**Files:**
- Create: `backend/app/services/task.py`
- Modify: `backend/app/routers/tasks.py` (viết lại toàn bộ, 43 dòng)
- Test: `backend/tests/test_service_task.py` (tạo mới)

**Interfaces:**
- Consumes: `app.errors.NotFoundError`, `app.models.Employee`, `app.models.Kpi`, `app.models.Task`; `app.services.kpi.create_kpi` và `app.services.employee.create_employee` (Task 1, 2) chỉ dùng trong test.
- Produces:
  - `list_tasks(db: Session) -> list[Task]`
  - `create_task(db: Session, *, title: str, kpi_id: int, assignee_id: int) -> Task`
  - `update_task(db: Session, task_id: int, changes: dict[str, Any]) -> Task`

Không có `get_task` công khai: backend không có endpoint `GET /api/tasks/{id}`, nên hàm nạp task là `_load_task` riêng tư (YAGNI).

- [ ] **Step 1: Viết test thất bại cho service**

Tạo `backend/tests/test_service_task.py`:

```python
from datetime import date

import pytest

from app.errors import NotFoundError
from app.models import TaskStatus
from app.services import employee as employee_service
from app.services import kpi as kpi_service
from app.services import task as task_service


def make_fixtures(db_session):
    owner = employee_service.create_employee(
        db_session, name="Chu viec", email="owner@example.com"
    )
    kpi = kpi_service.create_kpi(
        db_session,
        name="Hop dong ky moi",
        target_value=100.0,
        unit="hop dong",
        owner_id=owner.id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
    )
    return owner, kpi


def test_create_task_defaults_to_todo(db_session):
    owner, kpi = make_fixtures(db_session)

    created = task_service.create_task(
        db_session, title="Chot hop dong khach X", kpi_id=kpi.id, assignee_id=owner.id
    )

    assert created.id is not None
    assert created.status is TaskStatus.TODO


def test_create_task_with_unknown_kpi_raises_not_found(db_session):
    owner, _ = make_fixtures(db_session)

    with pytest.raises(NotFoundError):
        task_service.create_task(
            db_session, title="x", kpi_id=999999, assignee_id=owner.id
        )


def test_create_task_with_unknown_assignee_raises_not_found(db_session):
    _, kpi = make_fixtures(db_session)

    with pytest.raises(NotFoundError):
        task_service.create_task(
            db_session, title="x", kpi_id=kpi.id, assignee_id=999999
        )


def test_update_task_applies_changes(db_session):
    owner, kpi = make_fixtures(db_session)
    task = task_service.create_task(
        db_session, title="Viec A", kpi_id=kpi.id, assignee_id=owner.id
    )

    updated = task_service.update_task(
        db_session, task.id, {"status": TaskStatus.DOING}
    )

    assert updated.status is TaskStatus.DOING


def test_update_unknown_task_raises_not_found(db_session):
    with pytest.raises(NotFoundError):
        task_service.update_task(db_session, 999999, {"title": "x"})


def test_list_tasks_is_ordered_by_id(db_session):
    owner, kpi = make_fixtures(db_session)
    first = task_service.create_task(
        db_session, title="Viec 1", kpi_id=kpi.id, assignee_id=owner.id
    )
    second = task_service.create_task(
        db_session, title="Viec 2", kpi_id=kpi.id, assignee_id=owner.id
    )

    assert [row.id for row in task_service.list_tasks(db_session)] == [
        first.id,
        second.id,
    ]
```

- [ ] **Step 2: Chạy test, xác nhận nó fail**

```powershell
cd D:\projects\task-and-kpi\backend
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest tests/test_service_task.py -q
```

Kỳ vọng: FAIL với `ModuleNotFoundError: No module named 'app.services.task'`.

- [ ] **Step 3: Viết `backend/app/services/task.py`**

```python
"""Nghiệp vụ Task. Router chỉ dịch HTTP; mọi quyết định nghiệp vụ và ranh giới
giao dịch nằm ở đây.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Employee, Kpi, Task


def _load_task(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise NotFoundError(f"Không tìm thấy task {task_id}")
    return task


def list_tasks(db: Session) -> list[Task]:
    return list(db.scalars(select(Task).order_by(Task.id)).all())


def create_task(db: Session, *, title: str, kpi_id: int, assignee_id: int) -> Task:
    if db.get(Kpi, kpi_id) is None:
        raise NotFoundError(f"Không tìm thấy KPI {kpi_id}")
    if db.get(Employee, assignee_id) is None:
        raise NotFoundError(f"Không tìm thấy nhân viên {assignee_id}")

    task = Task(title=title, kpi_id=kpi_id, assignee_id=assignee_id)
    try:
        db.add(task)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(task)
    return task


def update_task(db: Session, task_id: int, changes: dict[str, Any]) -> Task:
    task = _load_task(db, task_id)

    for field, value in changes.items():
        setattr(task, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(task)
    return task
```

- [ ] **Step 4: Chạy lại test service, xác nhận pass**

```powershell
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest tests/test_service_task.py -q
```

Kỳ vọng: `6 passed`.

- [ ] **Step 5: Viết lại `backend/app/routers/tasks.py` cho mỏng**

Thay **toàn bộ** nội dung file bằng:

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Task
from app.schemas import TaskCreate, TaskOut, TaskUpdate
from app.services import task as task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)) -> list[Task]:
    return task_service.list_tasks(db)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    return task_service.create_task(db, **payload.model_dump())


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)
) -> Task:
    # exclude_none: xem ghi chú cùng chỗ trong routers/kpis.py.
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    return task_service.update_task(db, task_id, changes)
```

- [ ] **Step 6: Chạy toàn bộ test backend + kiểm bằng mắt rằng ba router đã sạch**

```powershell
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest -q
Select-String -Path app\routers\employees.py,app\routers\kpis.py,app\routers\tasks.py -Pattern "db\.commit|db\.add|db\.rollback|db\.get|select\("
```

Kỳ vọng: `145 passed` (139 + 6 mới), và lệnh `Select-String` **không in ra dòng nào**.

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/task.py backend/app/routers/tasks.py backend/tests/test_service_task.py
git commit -m "refactor(tasks): tach nghiep vu sang services/task.py"
```

---

### Task 4: `CheckConstraint` cho `kpis` trong `models.py`

**Files:**
- Modify: `backend/app/models.py:8-17` (import) và `backend/app/models.py:67-68` (khai báo `Kpi`)
- Test: `backend/tests/test_models.py` (thêm 2 test vào cuối file)

**Interfaces:**
- Consumes: `sqlalchemy.CheckConstraint`.
- Produces: hai ràng buộc tên `ck_kpis_period_order` và `ck_kpis_target_positive` trên bảng `kpis`. Không có API Python mới.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `backend/tests/test_models.py` (file đã `import pytest`, `IntegrityError`, `date`, `Employee`, `Kpi` sẵn):

```python
def test_inverted_period_is_rejected_by_db(db_session):
    """Ràng buộc spec §5 phải sống ở tầng DB, không chỉ ở Pydantic — SQL thô
    hay seed data ghi thẳng vào DB cũng không được lách."""
    employee = Employee(name="H", email="h@example.com")
    db_session.add(employee)
    db_session.flush()

    db_session.add(
        Kpi(
            name="Ky nguoc",
            target_value=10.0,
            unit="cai",
            owner_id=employee.id,
            period_start=date(2026, 12, 31),
            period_end=date(2026, 1, 1),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_non_positive_target_is_rejected_by_db(db_session):
    employee = Employee(name="I", email="i@example.com")
    db_session.add(employee)
    db_session.flush()

    db_session.add(
        Kpi(
            name="Muc tieu bang 0",
            target_value=0.0,
            unit="cai",
            owner_id=employee.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 12, 31),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
```

- [ ] **Step 2: Chạy test, xác nhận nó fail**

```powershell
cd D:\projects\task-and-kpi\backend
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest tests/test_models.py -q
```

Kỳ vọng: 2 test mới FAIL với `DID NOT RAISE <class 'sqlalchemy.exc.IntegrityError'>` — hiện chưa có ràng buộc nào.

- [ ] **Step 3: Thêm `CheckConstraint` vào import**

Sửa khối import ở `backend/app/models.py:8-17` thành (thêm đúng một dòng `CheckConstraint,` ngay sau `from sqlalchemy import (`):

```python
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
```

- [ ] **Step 4: Khai báo `__table_args__` trên `Kpi`**

Sửa `backend/app/models.py`, chèn ngay sau dòng `__tablename__ = "kpis"`:

```python
class Kpi(Base):
    __tablename__ = "kpis"
    __table_args__ = (
        # Ràng buộc của spec §5, đặt ở tầng DB chứ không chỉ ở Pydantic: SQL thô
        # hoặc seed data ghi thẳng vào DB cũng không lách được. Dự án dùng
        # create_all chứ không có migration, nên DB cũ phải tạo lại mới có.
        CheckConstraint("period_end >= period_start", name="ck_kpis_period_order"),
        CheckConstraint("target_value > 0", name="ck_kpis_target_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
```

Phần thân còn lại của lớp `Kpi` giữ nguyên.

- [ ] **Step 5: Chạy toàn bộ test backend**

```powershell
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest -q
```

Kỳ vọng: `147 passed` (145 + 2 mới). Nếu có test nào **khác** đổ, nghĩa là nó đang tạo KPI vi phạm ràng buộc — dừng lại và báo, đừng nới ràng buộc.

- [ ] **Step 6: Commit**

```powershell
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat(models): them CheckConstraint cho period va target_value cua KPI"
```

---

### Task 5: `getKpi` trong `frontend/src/api.ts`

**Files:**
- Modify: `frontend/src/api.ts:71-74`
- Test: `frontend/src/lib/api.test.ts` (thêm 1 test + sửa dòng import)

**Interfaces:**
- Consumes: `request<T>` (nội bộ `api.ts`), kiểu `Kpi` từ `./types`, `API_BASE` (đã export).
- Produces: `getKpi(id: number): Promise<Kpi>`.

Quyết định đã chốt: `getKpi` tồn tại để `api.ts` khớp 1-1 với danh sách endpoint ở spec §9 — đó chính là hợp đồng mà spec frontend §6 đặt ra cho tầng API. Không có trang nào gọi nó và **không** được ép một trang nào gọi: `ReviewPage` đã nạp cả danh sách KPI cho dropdown, còn `updateKpi` đã trả về KPI mới. `lib/api.test.ts` là nơi gọi thật.

- [ ] **Step 1: Viết test thất bại**

Sửa dòng import đầu `frontend/src/lib/api.test.ts` thành:

```ts
import { API_BASE, ApiError, createEmployee, getDashboard, getKpi, listEmployees } from '../api'
```

Rồi thêm vào cuối khối `describe('request thành công', ...)`, ngay sau test `'gửi Content-Type json kèm body khi POST'`:

```ts
  it('getKpi gọi GET đúng đường dẫn một KPI', async () => {
    const stub = mockFetch({
      ok: true,
      status: 200,
      json: async () => ({ id: 7, name: 'Doanh thu', target_value: 100 }),
    })

    await expect(getKpi(7)).resolves.toMatchObject({ id: 7, name: 'Doanh thu' })
    expect(stub.mock.calls[0][0]).toBe(`${API_BASE}/api/kpis/7`)
    expect((stub.mock.calls[0][1] as RequestInit).method).toBe('GET')
  })
```

- [ ] **Step 2: Chạy test, xác nhận nó fail**

```powershell
cd D:\projects\task-and-kpi\frontend
npm test
```

Kỳ vọng: FAIL — `getKpi is not a function` hoặc lỗi import từ `../api`.

- [ ] **Step 3: Thêm `getKpi` vào `api.ts`**

Sửa `frontend/src/api.ts`, chèn một dòng giữa `listKpis` và `createKpi` (đúng thứ tự spec §6 liệt kê: `listKpis getKpi createKpi updateKpi`):

```ts
export const listKpis = () => request<Kpi[]>('/api/kpis')
export const getKpi = (id: number) => request<Kpi>(`/api/kpis/${id}`)
export const createKpi = (payload: KpiCreate) => request<Kpi>('/api/kpis', 'POST', payload)
```

- [ ] **Step 4: Chạy lại Vitest và kiểm kiểu**

```powershell
npm test
npm run build
```

Kỳ vọng: `26 passed` (25 cũ + 1 mới), và `npm run build` chạy xong không lỗi.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/api.ts frontend/src/lib/api.test.ts
git commit -m "feat(frontend): them getKpi cho khop danh sach endpoint spec"
```

---

### Task 6: `frontend/tsconfig.node.json`

**Files:**
- Create: `frontend/tsconfig.node.json`
- Modify: `frontend/tsconfig.json` (thêm khối `references`)

**Interfaces:**
- Consumes: không có.
- Produces: một project TypeScript thứ hai phủ `vite.config.ts` — file mà `"include": ["src"]` của `tsconfig.json` đang bỏ sót.

- [ ] **Step 1: Tạo `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 2: Trỏ `tsconfig.json` tới nó**

Thêm `"references"` vào `frontend/tsconfig.json`, ngay sau dòng `"include": ["src"]`:

```json
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
```

(Nhớ dấu phẩy sau `["src"]`.) `npm run build` chạy `tsc --noEmit`, không phải `tsc -b`, nên `references` không kích hoạt việc emit — không có `.tsbuildinfo` hay `.d.ts` nào sinh ra.

- [ ] **Step 3: Kiểm rằng không có gì gãy và không có rác sinh ra**

```powershell
cd D:\projects\task-and-kpi\frontend
npm run build
npm test
git status --short
```

Kỳ vọng: `build` xong không lỗi, `26 passed`, và `git status` chỉ thấy `tsconfig.json` + `tsconfig.node.json` — **không** có `tsconfig.node.tsbuildinfo` hay `vite.config.d.ts`. Nếu có file rác, xoá nó và bỏ `composite: true` ra khỏi `tsconfig.node.json`.

- [ ] **Step 4: Kiểm rằng file mới thật sự có tác dụng**

```powershell
D:\projects\task-and-kpi\frontend\node_modules\.bin\tsc.cmd -p tsconfig.node.json --noEmit
```

Kỳ vọng: không lỗi — `vite.config.ts` type-check sạch dưới project mới.

- [ ] **Step 5: Commit**

```powershell
git add frontend/tsconfig.node.json frontend/tsconfig.json
git commit -m "chore(frontend): them tsconfig.node.json cho khop bo cuc spec"
```

---

### Task 7: Đồng bộ spec theo code (7 điểm)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md` (§5 employees, §5 kpi_progress_entries, §7.4, §8 validator, §8 providers, §9 dashboard)
- Modify: `docs/diagrams/class-diagram.md`, `docs/diagrams/component-diagram.md`, `docs/diagrams/sequence-approve.md`, `docs/diagrams/sequence-submit-report.md` (viết lại mục "Chỗ code lệch với spec")

Bảy điểm này là chỗ **code đúng hơn spec** — sửa spec, không sửa code. Không có test nào cho task này; cổng kiểm là đọc lại.

**Interfaces:**
- Consumes: không có.
- Produces: không có API. Task 9 trích dẫn các mục này trong mô tả PR.

- [ ] **Step 1: §5 `employees` — ghi rõ UNIQUE email**

Trong `docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md`, thay:

```
### employees
`id, name, email, created_at`
```

bằng:

```
### employees
`id, name, email, created_at`

**Ràng buộc UNIQUE `email`** — mỗi nhân viên một địa chỉ. Vi phạm trả HTTP 409,
cùng luật mã lỗi với mục 7.1.
```

- [ ] **Step 2: §5 `kpi_progress_entries` — `source_suggestion_id` là nullable**

Thay:

```
### kpi_progress_entries
`id, kpi_id → kpis.id, delta_value (float), source_suggestion_id → kpi_update_suggestions.id,
effective_date (date), created_at`
```

bằng:

```
### kpi_progress_entries
`id, kpi_id → kpis.id, delta_value (float),
source_suggestion_id (nullable, → kpi_update_suggestions.id),
effective_date (date), created_at`

`source_suggestion_id` để `nullable` vì sổ cái còn phải chứa được những dòng
không sinh ra từ một đề xuất (số liệu nhập tay, seed data, dữ liệu nhập trước
khi có luồng duyệt). Đường duyệt thì luôn điền nó — xem mục 7.4.
```

- [ ] **Step 3: §7.4 — nguồn gốc ràng buộc `final_kpi_id` và cổng `isfinite` thứ hai**

Thay hai đoạn:

```
`final_kpi_id` bắt buộc phải khác `null` khi duyệt — đây là chỗ quản lý gán KPI
cho những đề xuất LLM trả về `kpi_id = null`.

`final_delta` bắt buộc phải là số hữu hạn; một giá trị không hữu hạn (vô cực
hoặc NaN) bị từ chối với **HTTP 422** và không mutation nào được thực hiện.
```

bằng:

```
`final_kpi_id` bắt buộc phải khác `null` khi duyệt — đây là chỗ quản lý gán KPI
cho những đề xuất LLM trả về `kpi_id = null`. Ràng buộc này không phải một lệnh
`if` riêng: nó đến từ kiểu `final_kpi_id: int` (không `| None`) trong
`KpiApproveIn`, nên gửi `null` qua HTTP bị Pydantic chặn thành **422**. Gọi thẳng
`approve_kpi_suggestion(...)` ở tầng service với `final_kpi_id=None` thì chỉ bị
chặn gián tiếp — `db.get(Kpi, None)` trả `None` → `NotFoundError` → 404, không
phải 422.

`final_delta` bắt buộc phải là số hữu hạn; một giá trị không hữu hạn (vô cực
hoặc NaN) bị từ chối với **HTTP 422** và không mutation nào được thực hiện. Ràng
buộc này có **hai** cổng: `allow_inf_nan=False` trên `KpiApproveIn` ở biên HTTP,
và `math.isfinite(final_delta)` trong `approve_kpi_suggestion`. Cổng thứ hai ném
`InvalidInputError` (cũng ra 422) và tồn tại để đường gọi service trực tiếp —
không qua HTTP — cũng không lách được.
```

- [ ] **Step 4: §8 — đường xử lý JSON hỏng không đi qua validator**

Thay:

```
Validator từ chối:

- `kpi_id` / `task_id` / `related_kpi_id` không `null` nhưng không nằm trong catalog đã gửi.
- `delta_value` không phải số hữu hạn (NaN, vô cực).
- JSON không parse được hoặc thiếu khoá bắt buộc.

Mọi trường hợp trượt đều dẫn tới `extraction_status = failed` như mục 7.2.
```

bằng:

```
`validate_extraction_result` (ở `llm/base.py`, được `services/extraction.py` gọi
sau **mọi** provider) từ chối:

- `kpi_id` / `task_id` / `related_kpi_id` không `null` nhưng không nằm trong catalog đã gửi.
- `delta_value` không phải số hữu hạn (NaN, vô cực).

JSON không parse được hoặc thiếu khoá bắt buộc **không** đi qua validator này —
tới lượt nó chạy thì đã có sẵn một `ExtractionResult` hợp lệ trong tay. Hai ca đó
bị chặn sớm hơn, ở hai chỗ khác nhau:

- JSON hỏng, lỗi SDK, `stop_reason == "refusal"` → `AnthropicProvider` bọc mọi
  `Exception` của SDK thành `ExtractionError`.
- Thiếu khoá bắt buộc → Pydantic ném `ValidationError` ngay khi dựng `ExtractionResult`.

`run_extraction` bắt cả `ExtractionError` lẫn `ValidationError`, nên mọi trường
hợp trượt vẫn dẫn tới `extraction_status = failed` như mục 7.2 — giống kết quả,
khác đường đi.
```

- [ ] **Step 5: §8 — `ScriptedProvider` là một lớp riêng**

Thay:

```
- **MockProvider** — mặc định, không dùng mạng. Khớp từ khoá tên KPI/Task trong
  catalog và bắt số bằng regex; đủ thật để test trọn vòng có ý nghĩa. Nhận được
  kịch bản đóng sẵn khi unit test cần một kết quả cụ thể (kể cả kết quả hỏng).
```

bằng:

```
- **MockProvider** — mặc định (`name = "mock"`), không dùng mạng. Khớp từ khoá tên
  KPI/Task trong catalog và bắt số bằng regex; đủ thật để test trọn vòng có ý nghĩa.
  Không nhận kịch bản nào.
- **ScriptedProvider** — lớp riêng (`name = "scripted"`) trong cùng `llm/mock.py`,
  chỉ dùng cho unit test: nhận sẵn một `result` hoặc một `error` và trả/ném đúng
  thứ đó. Tách khỏi `MockProvider` để đường mặc định không phải mang thêm một
  nhánh "nếu có kịch bản thì..." mà chỉ test mới đi qua. `factory.get_provider`
  không bao giờ trả về nó — test tự dựng và tiêm qua `dependency_overrides`.
```

- [ ] **Step 6: §9 — `GET /api/dashboard` trả tập cha**

Thay dòng trong khối endpoint:

```
GET              /api/dashboard                      # mỗi KPI: actual, target, percent, expected, status
```

bằng:

```
GET              /api/dashboard                      # mỗi KPI: một DashboardItemOut, xem bên dưới
```

Rồi thêm đoạn này ngay trước đoạn "Quy ước mã lỗi:":

```
`GET /api/dashboard` trả cho mỗi KPI một `DashboardItemOut` gồm số liệu đánh giá
(`actual_value`, `target_value`, `expected_value`, `percent_complete`, `status`,
`at_risk`) **và** ngữ cảnh hiển thị (`kpi_id`, `kpi_name`, `unit`, `owner_name`,
`period_start`, `period_end`) — cùng lý do với `GET /api/suggestions`: trang
Dashboard vẽ được một hàng đầy đủ mà không phải gọi thêm API nào. Trang này dùng
hết cả tập đó.
```

- [ ] **Step 7: Viết lại mục "Chỗ code lệch với spec" trong `docs/diagrams/class-diagram.md`**

Thay toàn bộ mục cuối cùng của file bằng:

```markdown
## Chỗ đã đồng bộ

1. `kpi_progress_entries.source_suggestion_id` — code khai báo `nullable=True`
   (`models.py:196`), spec §5 trước đây viết như thể bắt buộc. **Đã sửa spec theo code:**
   §5 giờ ghi `(nullable, → kpi_update_suggestions.id)` kèm lý do. Sơ đồ vẽ `0..1`, đúng.
2. `employees.email UNIQUE` — code có `unique=True` (`models.py:63`), spec §5 trước đây
   không nêu. **Đã sửa spec theo code.**
3. `period_end >= period_start` và `target_value > 0` — spec §5 đòi, `models.py` trước đây
   không có `CheckConstraint` nào và hai ràng buộc chỉ sống ở tầng Pydantic.
   **Đã sửa code theo spec:** `Kpi.__table_args__` giờ có `ck_kpis_period_order` và
   `ck_kpis_target_positive`, nên SQL thô cũng không lách được. Dự án không có migration
   (`Base.metadata.create_all`), nên ràng buộc chỉ áp cho DB tạo mới — xem
   "Hạn chế đã biết" trong README.
```

- [ ] **Step 8: Viết lại `docs/diagrams/component-diagram.md`**

Trong khối mermaid, xoá ba dòng mũi tên lệch và hai dòng `classDef`/`class`:

```
    R_EMP -.->|"LỆCH SPEC: ghi thẳng DB"| DATA
    R_KPI -.->|"LỆCH SPEC: ghi thẳng DB"| DATA
    R_TASK -.->|"LỆCH SPEC: ghi thẳng DB"| DATA

    classDef drift stroke:#c0392b,stroke-width:2px,stroke-dasharray:4 3
    class R_EMP,R_KPI,R_TASK drift
```

thay bằng:

```
    R_EMP --> S_EMP
    R_KPI --> S_KPI
    R_TASK --> S_TASK
```

Và trong `subgraph SERVICES`, thêm ba node ngay sau `S_DASH`:

```
            S_EMP["employee.py<br/>list, create + kiểm email trùng"]
            S_KPI["kpi.py<br/>list, get, create, update<br/>+ kiểm kỳ ngược sau khi trộn PATCH"]
            S_TASK["task.py<br/>list, create, update"]
```

Rồi thêm ba cạnh tới DATA cạnh các cạnh service hiện có:

```
    S_EMP --> DATA
    S_KPI --> DATA
    S_TASK --> DATA
```

Cuối cùng thay mục "Chỗ code lệch với spec" bằng:

```markdown
## Chỗ đã đồng bộ

1. **Ba router CRUD giờ đã có service.** Spec §4 quy định "`routers` chỉ dịch HTTP ↔ service,
   không chứa quyết định nghiệp vụ". `routers/employees.py`, `routers/kpis.py`,
   `routers/tasks.py` trước đây tự `db.add` / `setattr` / `db.commit` và tự chứa nghiệp vụ.
   **Đã sửa code theo spec:** `services/employee.py`, `services/kpi.py`, `services/task.py`
   nhận toàn bộ quyết định (email trùng, kỳ ngược, khoá ngoại có tồn tại không) và cả
   ranh giới giao dịch. Ba router chỉ còn gọi service và trả kết quả — hành vi HTTP không đổi.
2. **`frontend/src/api.ts` đã có `getKpi`.** Khớp đủ danh sách hàm mà spec frontend §6 liệt kê.
   Không trang nào gọi nó: `ReviewPage` đã nạp cả danh sách KPI cho dropdown, `updateKpi`
   đã trả về KPI mới. `api.ts` khớp 1-1 với danh sách endpoint §9 là hợp đồng của tầng API,
   và `lib/api.test.ts` là nơi gọi thật.
3. **`frontend/tsconfig.node.json` đã tồn tại**, phủ `vite.config.ts` — file mà
   `"include": ["src"]` của `tsconfig.json` bỏ sót.
4. **`ScriptedProvider` là một lớp riêng.** **Đã sửa spec theo code:** §8 giờ liệt kê nó
   tách khỏi `MockProvider` kèm lý do.
5. **`GET /api/dashboard` trả tập cha.** **Đã sửa spec theo code:** §9 giờ liệt kê đủ
   `DashboardItemOut`.

## Còn lại, đã ghi nhận chứ chưa sửa

- `routers/reports.py:29` vẫn tự kiểm `db.get(Employee, ...)` và tự ném `NotFoundError`.
  Cùng loại với ba chỗ trên nhưng nằm trên đường trích xuất, nên để riêng ra ngoài
  phạm vi lần này.
```

- [ ] **Step 9: Viết lại `docs/diagrams/sequence-approve.md`**

Thay mục "Chỗ code lệch với spec" bằng:

```markdown
## Chỗ đã đồng bộ

1. **`final_kpi_id` khác `null`.** Spec §7.4 nói "bắt buộc", code không có `if` tường minh —
   ràng buộc đến từ kiểu `final_kpi_id: int` trong `KpiApproveIn`. **Đã sửa spec theo code:**
   §7.4 giờ nói rõ ràng buộc đến từ đâu, và rằng gọi thẳng service với `None` cho 404 chứ
   không phải 422.
2. **Cổng `math.isfinite` thứ hai** trong `approval.py:57` mà spec không mô tả — chặt hơn
   spec, không lỏng hơn. **Đã sửa spec theo code:** §7.4 giờ mô tả cả hai cổng.

## Còn lại, đã ghi nhận chứ chưa sửa

- `db.refresh(suggestion)` sau `commit` trong khi `sessionmaker` đặt `expire_on_commit=False`
  (`db.py:17`) — một vòng SELECT thừa. Không sai, chỉ thừa; ba service mới
  (`employee`/`kpi`/`task`) cố ý giữ cùng idiom để cả tầng `services/` nhất quán.
```

- [ ] **Step 10: Viết lại `docs/diagrams/sequence-submit-report.md`**

Thay mục "Chỗ code lệch với spec" bằng:

```markdown
## Chỗ đã đồng bộ

1. **JSON hỏng / thiếu khoá không đi qua validator.** Spec §8 trước đây xếp chúng vào phần
   việc của `validate_extraction_result`; thực tế validator chỉ kiểm hai bất biến (id trong
   catalog, delta hữu hạn), còn JSON hỏng do `AnthropicProvider` bọc thành `ExtractionError`
   và thiếu khoá nổi lên thành `ValidationError` của Pydantic. **Đã sửa spec theo code:**
   §8 giờ mô tả đúng ba đường, và nói rõ cả ba đều về `failed`.

## Còn lại, đã ghi nhận chứ chưa sửa

1. **Check-then-insert.** Spec §5 + §7.1 nói ràng buộc trùng tuần là
   `UNIQUE (employee_id, week_start)` và "vi phạm trả 409"; code kiểm bằng `SELECT` trước
   (`extraction.py:114`) rồi mới `INSERT`. Hai request đồng thời lọt qua cả hai lần `SELECT`,
   và request thua cuộc nhận `IntegrityError` không được bắt → **500 thay vì 409**.
   `services/employee.py` có đúng cùng dạng này với email trùng. Đã ghi vào mục
   "Hạn chế đã biết" của README kèm cách sửa đúng; MVP chấp nhận đánh đổi.
2. **`routers/reports.py:29` tự kiểm `db.get(Employee, ...)`** và tự ném `NotFoundError` —
   một quyết định nghiệp vụ nằm trong router, giống ba router CRUD trước khi được tách.
   Để ngoài phạm vi lần này vì nó nằm trên đường trích xuất.
```

- [ ] **Step 11: Đọc lại và kiểm mermaid còn render được**

```powershell
cd D:\projects\task-and-kpi
Select-String -Path docs\diagrams\*.md -Pattern "LỆCH SPEC|Chỗ code lệch"
Select-String -Path docs\superpowers\specs\2026-09-11-kpi-report-ai-design.md -Pattern "JSON không parse được hoặc thiếu khoá bắt buộc"
```

Kỳ vọng: cả hai lệnh **không in ra dòng nào**. Sau đó mở `docs/diagrams/component-diagram.md`, đọc lại khối mermaid và xác nhận mọi node được tham chiếu (`S_EMP`, `S_KPI`, `S_TASK`) đều đã được khai báo bên trong `subgraph SERVICES`.

- [ ] **Step 12: Commit**

```powershell
git add docs/superpowers/specs/2026-09-11-kpi-report-ai-design.md docs/diagrams/
git commit -m "docs: dong bo spec theo code va commit bon so do"
```

---

### Task 8: README — mục "Hạn chế đã biết"

**Files:**
- Modify: `README.md` (thêm mục mới ở cuối file)

**Interfaces:**
- Consumes: không có.
- Produces: không có.

- [ ] **Step 1: Thêm mục vào cuối `README.md`**

Chèn vào cuối file, sau mục "Kiểm thử trọn vòng":

```markdown
## Hạn chế đã biết

- **Check-then-insert: hai request đồng thời cho 500 thay vì 409.**
  `POST /api/employees` (email trùng) và `POST /api/reports` (trùng
  `employee_id` + `week_start`) đều kiểm bằng một `SELECT` trước rồi mới `INSERT`.
  Ràng buộc `UNIQUE` ở tầng DB vẫn là lưới đỡ cuối cùng, nhưng hai request đến
  cùng lúc sẽ cùng lọt qua vòng `SELECT`; request thua cuộc nhận `IntegrityError`
  không được bắt và thoát ra thành **HTTP 500** thay vì **409** như spec quy định.
  Với một tổ nhỏ nhập liệu bằng tay thì xác suất này gần bằng không nên MVP chấp
  nhận đánh đổi; cách sửa đúng là bắt `IntegrityError` quanh `commit` rồi dịch
  thành `ConflictError`, và bỏ hẳn vòng `SELECT` kiểm trước.

- **`CheckConstraint` chỉ áp cho database tạo mới.** Dự án dùng
  `Base.metadata.create_all` chứ không có migration, nên hai ràng buộc
  `period_end >= period_start` và `target_value > 0` trên bảng `kpis` chỉ tồn tại
  trong database được tạo sau thay đổi này. Một file `kpi.db` cũ phải xoá đi cho
  tạo lại mới có chúng.
```

- [ ] **Step 2: Đọc lại**

```powershell
Get-Content D:\projects\task-and-kpi\README.md -Tail 25
```

Kỳ vọng: mục "Hạn chế đã biết" hiện ra đầy đủ hai gạch đầu dòng.

- [ ] **Step 3: Commit**

```powershell
git add README.md
git commit -m "docs(readme): ghi lai han che check-then-insert va pham vi CheckConstraint"
```

---

### Task 9: Kiểm thử toàn bộ và mở Pull Request

**Files:** không sửa file nào (trừ khi bước kiểm phát hiện lỗi).

**Interfaces:**
- Consumes: kết quả của Task 1-8.
- Produces: một Pull Request trên `AnhDuc-creator/task-and-kpi` từ nhánh `fix/spec-drift-services` vào `main`.

- [ ] **Step 1: Chạy toàn bộ test backend**

```powershell
cd D:\projects\task-and-kpi\backend
D:\projects\task-and-kpi\.venv\Scripts\python.exe -m pytest -q
```

Kỳ vọng: `147 passed` — 129 test cũ **không** đổi, cộng 16 test service mới và 2 test model mới.

- [ ] **Step 2: Chạy Vitest**

```powershell
cd D:\projects\task-and-kpi\frontend
npm test
npm run build
```

Kỳ vọng: `26 passed` (25 cũ + 1 mới), `build` không lỗi.

- [ ] **Step 3: Chạy e2e lần thứ nhất**

```powershell
cd D:\projects\task-and-kpi
D:\projects\task-and-kpi\.venv\Scripts\python.exe tests\e2e\run_e2e.py
```

Kỳ vọng: exit code 0. Nếu script từ chối chạy vì cổng 8000/5173 đang bị giữ, giải phóng cổng rồi chạy lại — **không** sửa script.

- [ ] **Step 4: Chạy e2e lần thứ hai**

```powershell
D:\projects\task-and-kpi\.venv\Scripts\python.exe tests\e2e\run_e2e.py
```

Kỳ vọng: exit code 0 lần nữa. Chạy hai lần là để chứng minh kịch bản lặp lại được — lần hai chạy trên một DB sạch mới, không phải trên dư âm của lần một.

- [ ] **Step 5: Kiểm lần cuối rằng ba router đã sạch nghiệp vụ**

```powershell
Select-String -Path backend\app\routers\employees.py,backend\app\routers\kpis.py,backend\app\routers\tasks.py -Pattern "db\.commit|db\.add|db\.rollback|db\.get|select\(|ConflictError|InvalidInputError|NotFoundError"
```

Kỳ vọng: **không in ra dòng nào**.

- [ ] **Step 6: Đẩy nhánh lên GitHub**

```powershell
cd D:\projects\task-and-kpi
git push -u origin fix/spec-drift-services
```

- [ ] **Step 7: Mở Pull Request**

```powershell
gh pr create --base main --head fix/spec-drift-services --title "fix: dong bo code va spec o 4 + 7 diem lech" --body-file <đường dẫn file mô tả>
```

Mô tả PR phải nêu: 4 chỗ sửa code theo spec, 7 chỗ sửa spec theo code, mục README mới, con số test trước/sau (129 → 147 backend, 25 → 26 Vitest, e2e xanh 2 lần), và ghi rõ những gì **cố ý không** làm (`routers/reports.py`, `db.refresh` thừa, check-then-insert). Kết thúc mô tả bằng hai dòng attribution mà phiên làm việc yêu cầu.

- [ ] **Step 8: In ra link PR và dừng**

**Không** merge. Không xoá worktree. Báo lại link PR.

---

## Self-Review

**Spec coverage.** Bốn chỗ lệch code→spec: Task 1-3 (routers), Task 4 (CheckConstraint), Task 5 (getKpi), Task 6 (tsconfig.node.json) ✓. Bảy chỗ lệch spec→code: `source_suggestion_id` (T7.2), `email UNIQUE` (T7.1), JSON hỏng (T7.4), `final_kpi_id` (T7.3), cổng `isfinite` thứ hai (T7.3), `ScriptedProvider` (T7.5), `DashboardItemOut` (T7.6) ✓. README (T8) ✓. Test + PR (T9) ✓.

**Placeholder scan.** Chỗ duy nhất chưa có nội dung cụ thể là `--body-file <đường dẫn>` ở Task 9 Step 7 — có chủ đích, vì mô tả PR chỉ viết được sau khi biết kết quả thật của các bước kiểm. Nội dung bắt buộc của nó đã liệt kê đủ ngay dưới.

**Type consistency.** `employee_service.create_employee(db, *, name, email)` ← router gọi `**payload.model_dump()` với `EmployeeCreate{name, email}` ✓. `kpi_service.create_kpi(db, *, name, target_value, unit, owner_id, period_start, period_end)` ← `KpiCreate` có đúng 6 trường đó ✓. `task_service.create_task(db, *, title, kpi_id, assignee_id)` ← `TaskCreate` ✓. `update_kpi(db, kpi_id, changes)` / `update_task(db, task_id, changes)` — cùng chữ ký, cùng thứ tự tham số ✓. `get_kpi` công khai (router cần), `_load_task` riêng tư (không có endpoint) — chênh lệch có chủ đích, đã ghi lý do ✓.

**Rủi ro đã lường.**
- Test dùng **chung một `db_session`** cho cả TestClient lẫn assertion, nên `db.rollback()` trong `update_kpi` là thứ giữ cho `test_patch_cannot_create_inverted_period` xanh. Không được bỏ.
- `CheckConstraint` có thể làm đổ một test cũ nào đó nếu nó tạo KPI vi phạm. Task 4 Step 5 nói rõ: dừng và báo, đừng nới ràng buộc.
- `composite: true` trong `tsconfig.node.json` có thể sinh file rác nếu ai đó chạy `tsc -b`. Task 6 Step 3 kiểm `git status` để bắt.
- Số test cuối cùng (147 / 26) là **suy ra**; nếu con số thật lệch, đếm lại và báo — đừng sửa test cho khớp số.
