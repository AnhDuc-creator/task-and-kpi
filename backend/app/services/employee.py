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
