"""Kịch bản trọn vòng: tạo dữ liệu → nộp báo cáo → duyệt → dashboard đổi số.

Server do `run_e2e.py` khởi động sẵn. Luôn mở frontend qua `localhost:5173`,
không dùng `127.0.0.1` — backend chỉ mở CORS cho đúng origin đó.
"""

from __future__ import annotations

import datetime as dt
import pathlib

from playwright.sync_api import expect, sync_playwright

BASE_URL = "http://localhost:5173"

KPI_NAME = "Doanh so"
TASK_TITLE = "Goi khach hang moi"
EMPLOYEE_NAME = "Le Van A"
EMPLOYEE_EMAIL = "levana@example.com"

# Kỳ đã trôi qua phần lớn: expected xấp xỉ 86% của chỉ tiêu, nên actual = 0
# chắc chắn rơi vào "Có nguy cơ" theo ngưỡng 0.8 trong rules.py.
TODAY = dt.date.today()
PERIOD_START = (TODAY - dt.timedelta(days=60)).isoformat()
PERIOD_END = (TODAY + dt.timedelta(days=10)).isoformat()
WEEK_START = (TODAY - dt.timedelta(days=TODAY.weekday())).isoformat()

# MockProvider khớp tên KPI / tiêu đề task trong từng dòng và lấy **số đầu tiên
# trên dòng** làm delta, nên dòng đầu phải có 40 là con số đầu tiên.
REPORT_TEXT = "\n".join(
    [
        f"{KPI_NAME} tang them 40 trieu trong tuan nay",
        f"{TASK_TITLE} da hoan thanh",
        "Vuong mac: thieu du lieu tu phong ke toan",
    ]
)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda message: print(f"[console:{message.type}] {message.text}"))

        try:
            # --- Thiết lập: nhân viên, KPI, công việc -------------------------
            page.goto(f"{BASE_URL}/setup")
            page.wait_for_load_state("networkidle")

            page.get_by_test_id("employee-form-name").fill(EMPLOYEE_NAME)
            page.get_by_test_id("employee-form-email").fill(EMPLOYEE_EMAIL)
            page.get_by_test_id("employee-form-submit").click()
            expect(page.get_by_test_id("employee-row")).to_have_count(1)

            page.get_by_test_id("kpi-form-name").fill(KPI_NAME)
            page.get_by_test_id("kpi-form-target").fill("100")
            page.get_by_test_id("kpi-form-unit").fill("trieu")
            page.get_by_test_id("kpi-form-owner").select_option(label=EMPLOYEE_NAME)
            page.get_by_test_id("kpi-form-start").fill(PERIOD_START)
            page.get_by_test_id("kpi-form-end").fill(PERIOD_END)
            page.get_by_test_id("kpi-form-submit").click()
            expect(page.get_by_test_id("kpi-row")).to_have_count(1)

            page.get_by_test_id("task-form-title").fill(TASK_TITLE)
            page.get_by_test_id("task-form-kpi").select_option(label=KPI_NAME)
            page.get_by_test_id("task-form-assignee").select_option(label=EMPLOYEE_NAME)
            page.get_by_test_id("task-form-submit").click()
            expect(page.get_by_test_id("task-row")).to_have_count(1)
            print("OK  Thiet lap: tao nhan vien, KPI, cong viec")

            # --- Dashboard trước khi duyệt: phải đang cảnh báo ----------------
            # Không kiểm bước này thì bước tắt cảnh báo ở cuối không chứng minh
            # được điều gì.
            page.goto(f"{BASE_URL}/dashboard")
            page.wait_for_load_state("networkidle")
            expect(page.get_by_test_id("kpi-card")).to_have_count(1)
            # percent_complete = actual/target = 0/100 = 0.0, và formatPercent nhân
            # 100 (thang phân số được test_rules.py:90/101 chốt), nên đúng "0%".
            expect(page.get_by_test_id("kpi-card-percent")).to_have_text("0%")
            expect(page.get_by_test_id("kpi-card-actual")).to_have_text("0 / 100 trieu")
            expect(page.get_by_test_id("kpi-card-status")).to_have_text("Có nguy cơ")
            print("OK  Dashboard truoc khi duyet: 0%, 0/100, Co nguy co")

            # --- Nộp báo cáo ---------------------------------------------------
            page.goto(f"{BASE_URL}/report")
            page.wait_for_load_state("networkidle")
            page.get_by_test_id("report-employee").select_option(label=EMPLOYEE_NAME)
            page.get_by_test_id("report-week").fill(WEEK_START)
            page.get_by_test_id("report-text").fill(REPORT_TEXT)
            page.get_by_test_id("report-submit").click()

            expect(page.get_by_test_id("report-result")).to_be_visible()
            expect(page.get_by_test_id("report-status-badge").first).to_have_text("Đã trích xuất")
            expect(page.get_by_test_id("report-kpi-suggestion")).to_have_count(1)
            expect(page.get_by_test_id("report-task-suggestion")).to_have_count(1)
            expect(page.get_by_test_id("report-blocker")).to_have_count(1)
            print("OK  Nop bao cao: 1 de xuat KPI, 1 cong viec, 1 vuong mac")

            # --- Duyệt, có sửa số liệu ------------------------------------------
            page.goto(f"{BASE_URL}/review")
            page.wait_for_load_state("networkidle")
            expect(page.get_by_test_id("kpi-suggestion-row")).to_have_count(1)
            expect(page.get_by_test_id("task-suggestion-row")).to_have_count(1)

            # Sửa delta 40 → 100 để kiểm luôn đường final_* chứ không phải suggested_*.
            page.get_by_test_id("kpi-row-delta").fill("100")
            page.get_by_test_id("kpi-row-note").fill("Da doi chieu voi ke toan")
            page.get_by_test_id("kpi-row-approve").click()
            expect(page.get_by_test_id("kpi-suggestion-row")).to_have_count(0)

            page.get_by_test_id("task-row-approve").click()
            expect(page.get_by_test_id("queue-empty")).to_be_visible()
            print("OK  Duyet: sua delta thanh 100 va duyet ca hai de xuat")

            # --- Dashboard sau khi duyệt: đổi số và tắt cảnh báo ----------------
            page.goto(f"{BASE_URL}/dashboard")
            page.wait_for_load_state("networkidle")
            # actual/target = 100/100 = 1.0 → "100%". Đây chính là ca mà
            # test_rules.py:90 khẳng định percent_complete == 1.0.
            expect(page.get_by_test_id("kpi-card-percent")).to_have_text("100%")
            expect(page.get_by_test_id("kpi-card-actual")).to_have_text("100 / 100 trieu")
            expect(page.get_by_test_id("kpi-card-status")).to_have_text("Hoàn thành")
            # Cảnh báo đã tắt: không còn thẻ nào mang nhãn "Có nguy cơ".
            expect(page.get_by_text("Có nguy cơ")).to_have_count(0)
            expect(page.get_by_test_id("dashboard-blocker")).to_have_count(1)
            print("OK  Dashboard sau khi duyet: 100%, 100/100, Hoan thanh, canh bao da tat")

            # Đường dẫn tuyệt đối: script chạy với CWD là gốc repo, nhưng đừng
            # phụ thuộc vào đó. Ảnh nằm trong thư mục đã được .gitignore bỏ qua.
            shot_dir = pathlib.Path(__file__).resolve().parent / "screenshots"
            shot_dir.mkdir(exist_ok=True)
            page.screenshot(path=str(shot_dir / "dashboard-sau-khi-duyet.png"), full_page=True)
            print("\nTRON VONG THANH CONG")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
