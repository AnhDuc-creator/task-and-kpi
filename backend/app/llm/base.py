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
