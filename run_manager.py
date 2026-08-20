import json
import os
import subprocess
import sys
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_PATH = os.path.join(BASE_DIR, "run_status.json")
LOG_PATH = os.path.join(BASE_DIR, "run.log")
PYTHON = sys.executable  # the venv python running this Streamlit process


def _read_status():
    if not os.path.exists(STATUS_PATH):
        return {"status": "idle"}
    with open(STATUS_PATH) as f:
        return json.load(f)


def _write_status(status):
    with open(STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def get_status():
    status = _read_status()
    if status.get("status") == "running" and not _pid_alive(status.get("pid", -1)):
        status["status"] = "done"
        status["finished_at"] = datetime.datetime.now().isoformat()
        _write_status(status)
    return status


def start_run():
    status = get_status()
    if status.get("status") == "running":
        return status

    log_file = open(LOG_PATH, "w")
    proc = subprocess.Popen(
        [PYTHON, "-u", os.path.join(BASE_DIR, "run_daily.py")],
        stdout=log_file, stderr=subprocess.STDOUT,
        cwd=BASE_DIR, start_new_session=True,
    )
    status = {"status": "running", "pid": proc.pid, "started_at": datetime.datetime.now().isoformat(),
              "log_path": LOG_PATH}
    _write_status(status)
    return status


def tail_log(n=200):
    if not os.path.exists(LOG_PATH):
        return ""
    with open(LOG_PATH) as f:
        lines = f.readlines()
    return "".join(lines[-n:])
