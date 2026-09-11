"""Lỗi nghiệp vụ, không phụ thuộc HTTP. `main.py` ánh xạ chúng sang mã trạng thái."""


class ConflictError(Exception):
    """Thao tác không hợp lệ với trạng thái hiện tại (→ HTTP 409)."""


class NotFoundError(Exception):
    """Không tìm thấy bản ghi (→ HTTP 404)."""


class InvalidInputError(Exception):
    """Dữ liệu vào không hợp lệ mà Pydantic không tự bắt được (→ HTTP 422).

    Dùng cho ràng buộc chỉ kiểm được sau khi trộn dữ liệu gửi lên với dữ liệu
    đang lưu — ví dụ PATCH chỉ đổi `period_end` nhưng lại tạo ra kỳ ngược.
    """
