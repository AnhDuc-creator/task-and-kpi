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
