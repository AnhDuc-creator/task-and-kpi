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
