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
