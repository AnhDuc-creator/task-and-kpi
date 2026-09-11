"""Lỗi nghiệp vụ, không phụ thuộc HTTP. `main.py` ánh xạ chúng sang mã trạng thái."""


class ConflictError(Exception):
    """Thao tác không hợp lệ với trạng thái hiện tại (→ HTTP 409)."""


class NotFoundError(Exception):
    """Không tìm thấy bản ghi (→ HTTP 404)."""
