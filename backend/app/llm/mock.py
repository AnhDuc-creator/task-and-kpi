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
