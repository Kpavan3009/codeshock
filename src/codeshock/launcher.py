import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from .config import CodeshockConfig


SESSION_NAME = "codeshock"


def check_dependencies() -> dict:
    deps = {}
    for cmd in ["tmux", "claude", "codex"]:
        deps[cmd] = shutil.which(cmd) is not None
    return deps


def kill_existing_session():
    subprocess.run(
        ["tmux", "kill-session", "-t", SESSION_NAME],
        capture_output=True, timeout=5,
    )


def get_pane_sizes(ratio: str) -> tuple:
    parts = ratio.split(":")
    try:
        left = int(parts[0])
        right = int(parts[1])
        total = left + right
        left_pct = int(left / total * 100)
        return left_pct, 100 - left_pct
    except (ValueError, IndexError):
        return 70, 30


def launch_tmux_session(config: CodeshockConfig) -> bool:
    deps = check_dependencies()

    if not deps["tmux"]:
        print("Error: tmux is required. Install with: brew install tmux")
        return False

    if not deps["claude"]:
        print("Error: Claude Code CLI not found. Install from: https://claude.ai/download")
        return False

    if not deps["codex"]:
        print("Warning: Codex CLI not found. Reviews will fail.")
        print("Install with: npm i -g @openai/codex")

    kill_existing_session()

    left_pct, right_pct = get_pane_sizes(config.general.pane_ratio)

    project_dir = config.project_dir
    codeshock_dir = config.codeshock_dir

    subprocess.run([
        "tmux", "new-session", "-d",
        "-s", SESSION_NAME,
        "-c", project_dir,
        "-x", "200", "-y", "50",
    ], timeout=5)

    subprocess.run([
        "tmux", "send-keys", "-t", f"{SESSION_NAME}:0",
        f"claude", "Enter",
    ], timeout=5)

    subprocess.run([
        "tmux", "split-window", "-h",
        "-t", f"{SESSION_NAME}:0",
        "-c", project_dir,
        "-p", str(right_pct),
    ], timeout=5)

    dashboard_cmd = f"python -m codeshock dashboard --project-dir '{project_dir}'"
    subprocess.run([
        "tmux", "send-keys", "-t", f"{SESSION_NAME}:0.1",
        dashboard_cmd, "Enter",
    ], timeout=5)

    subprocess.run([
        "tmux", "select-pane", "-t", f"{SESSION_NAME}:0.0",
    ], timeout=5)

    return True


def attach_session():
    os.execvp("tmux", ["tmux", "attach-session", "-t", SESSION_NAME])


def is_session_running() -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", SESSION_NAME],
        capture_output=True, timeout=5,
    )
    return result.returncode == 0
