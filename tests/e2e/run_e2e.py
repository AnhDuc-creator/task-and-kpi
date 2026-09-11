"""Chạy kịch bản e2e trọn vòng, lặp lại được nhiều lần.

Ba việc phải làm trước khi giao cho `with_server.py`:

1. Xoá file SQLite tạm, để mỗi lần chạy bắt đầu từ database trống.
2. Giải phóng cổng 8000 và 5173. `with_server.py` spawn server bằng
   `shell=True` và khi dọn dẹp chỉ `terminate()` chính tiến trình đó — trên
   Windows đó là `cmd.exe` bọc ngoài, nên `node.exe` và `python.exe` con sống
   sót và tiếp tục giữ cổng. Không dọn thì lần chạy thứ hai chết ở
   "Server failed to start".
3. Đặt DATABASE_URL và LLM_PROVIDER cho tiến trình con.

Về `npm` trên Windows: `with_server.py` dùng `shell=True`, nên lệnh chạy qua
`cmd.exe /c` và `npm` được phân giải thành `npm.cmd` mà không cần gọi tường
minh. Dùng `cd /d` (có `/d`) để chuyển được cả ổ đĩa. `subprocess.run(..., env=env)`
ở dưới truyền env xuống `with_server.py`, và `with_server.py` spawn con bằng
`Popen` không đặt `env=`, nên hai server đều thừa hưởng DATABASE_URL.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
DB_PATH = BACKEND_DIR / ".e2e" / "kpi_e2e.db"
WITH_SERVER = REPO_ROOT / ".claude" / "skills" / "webapp-testing" / "scripts" / "with_server.py"
FLOW_SCRIPT = pathlib.Path(__file__).resolve().parent / "full_flow.py"
PORTS = (8000, 5173)


def pids_listening_on(port: int) -> set[str]:
    """PID của các tiến trình đang LISTEN trên `port` (chỉ Windows)."""
    if sys.platform != "win32":
        return set()
    result = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True
    )
    pids: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        # Proto | Local Address | Foreign Address | State | PID
        if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{port}"):
            pids.add(parts[4])
    return pids


def command_line_of(pid: str) -> str | None:
    """Command line đầy đủ của PID, hoặc None nếu không xác định được (chỉ Windows)."""
    if sys.platform != "win32":
        return None
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine",
            ],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    return output or None


def is_our_server(command_line: str) -> bool:
    """True nếu command line trông giống uvicorn hoặc Vite dev server do script này khởi động."""
    lowered = command_line.lower()
    if "uvicorn" in lowered and "app.main:app" in lowered:
        return True
    return "vite" in lowered or "npm" in lowered


def free_ports() -> None:
    """Giải phóng cổng 8000/5173, nhưng CHỈ kill tiến trình đúng là server của script này.

    Cổng 8000 là cổng mặc định rất phổ biến — nếu người dùng đang chạy
    `uvicorn --reload` thủ công ở cửa sổ khác, không được âm thầm kill nó.
    Nếu không xác định được, hoặc command line không khớp uvicorn/Vite của
    chúng ta, thì coi như "không phải của mình": cảnh báo và dừng lại, để
    người dùng tự giải phóng cổng thay vì kill nhầm.
    """
    for port in PORTS:
        for pid in pids_listening_on(port):
            command_line = command_line_of(pid)
            if command_line is None or not is_our_server(command_line):
                print(
                    f"CẢNH BÁO: cổng {port} đang bị tiến trình PID {pid} giữ, "
                    "và tiến trình này không giống server do kịch bản e2e này khởi động "
                    f"(command line: {command_line!r}). Sẽ KHÔNG tự ý kill. "
                    f"Vui lòng tự giải phóng cổng {port} (đóng tiến trình đó) rồi chạy lại."
                )
                sys.exit(1)
            print(f"Giải phóng cổng {port}: taskkill PID {pid} ({command_line})")
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", pid], capture_output=True
            )


def main() -> int:
    free_ports()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.unlink(missing_ok=True)

    env = dict(os.environ)
    # Biến môi trường có độ ưu tiên cao hơn file backend/.env trong
    # pydantic-settings, nên không cần sửa gì trong backend.
    env["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
    env["LLM_PROVIDER"] = "mock"

    backend_cmd = (
        f'cd /d "{BACKEND_DIR}" && '
        f'"{sys.executable}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000'
    )
    frontend_cmd = f'cd /d "{FRONTEND_DIR}" && npm run dev'

    command = [
        sys.executable,
        str(WITH_SERVER),
        "--server", backend_cmd, "--port", "8000",
        "--server", frontend_cmd, "--port", "5173",
        "--timeout", "90",
        "--", sys.executable, str(FLOW_SCRIPT),
    ]

    try:
        return subprocess.run(command, env=env).returncode
    finally:
        free_ports()


if __name__ == "__main__":
    raise SystemExit(main())
