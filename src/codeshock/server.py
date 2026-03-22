import asyncio
import json
import os
import pty
import select
import signal
import struct
import fcntl
import termios
import subprocess
import shutil
import time
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from .config import load_config, init_codeshock_dir
from .context import sync_context
from .session import SessionManager, ReviewRecord
from .watcher import CodeshockWatcher
from .reviewer import get_git_diff, run_codex_review, run_codex_chat, token_budget


app = FastAPI(title="codeshock")

WEB_DIR = Path(__file__).parent / "web"

STATE = {
    "config": None,
    "session": None,
    "watcher": None,
    "reviews": [],
    "project_dir": None,
}


def create_pty_process(cmd, cwd):
    pid, fd = pty.openpty()

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"

    child_pid = os.fork()
    if child_pid == 0:
        os.close(pid)
        os.setsid()

        os.dup2(fd, 0)
        os.dup2(fd, 1)
        os.dup2(fd, 2)
        if fd > 2:
            os.close(fd)

        os.chdir(cwd)
        os.execvpe(cmd[0], cmd, env)
    else:
        os.close(fd)
        return child_pid, pid


def set_pty_size(fd, rows, cols):
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    except Exception:
        pass


active_ptys = {}


@app.get("/")
async def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "project": STATE["project_dir"]}


@app.get("/api/reviews")
async def get_reviews():
    if STATE["session"]:
        return {
            "reviews": [r.to_dict() for r in STATE["session"].reviews[-20:]],
            "stats": {
                "total": STATE["session"].total_reviews,
                "issues": STATE["session"].total_issues,
                "avg_score": round(STATE["session"].avg_score, 1),
                "duration": STATE["session"].session_duration,
                "scores": STATE["session"].score_history[-20:],
                "hot_files": STATE["session"].hot_files(5),
                "recurring": STATE["session"].recurring_issues(5),
            },
        }
    return {"reviews": [], "stats": {}}


@app.websocket("/ws/terminal/{terminal_id}")
async def terminal_ws(websocket: WebSocket, terminal_id: str):
    await websocket.accept()

    project_dir = STATE["project_dir"] or os.getcwd()

    if terminal_id == "claude":
        claude_path = shutil.which("claude")
        if not claude_path:
            await websocket.send_text("\r\n  Error: claude CLI not found.\r\n")
            await websocket.close()
            return
        cmd = [claude_path]
    elif terminal_id == "codex":
        codex_path = shutil.which("codex")
        if not codex_path:
            await websocket.send_text("\r\n  Error: codex CLI not found.\r\n")
            await websocket.close()
            return
        cmd = [codex_path]
    else:
        await websocket.send_text("\r\n  Unknown terminal ID.\r\n")
        await websocket.close()
        return

    child_pid, master_fd = create_pty_process(cmd, project_dir)
    active_ptys[terminal_id] = {"pid": child_pid, "fd": master_fd}

    set_pty_size(master_fd, 40, 100)

    loop = asyncio.get_event_loop()

    async def read_output():
        while True:
            try:
                await asyncio.sleep(0.01)
                if select.select([master_fd], [], [], 0)[0]:
                    data = os.read(master_fd, 4096)
                    if data:
                        await websocket.send_bytes(data)
                    else:
                        break
            except OSError:
                break
            except WebSocketDisconnect:
                break

    read_task = asyncio.create_task(read_output())

    try:
        while True:
            msg = await websocket.receive()
            if "text" in msg:
                payload = json.loads(msg["text"])
                if payload.get("type") == "input":
                    os.write(master_fd, payload["data"].encode())
                elif payload.get("type") == "resize":
                    rows = payload.get("rows", 40)
                    cols = payload.get("cols", 100)
                    set_pty_size(master_fd, rows, cols)
            elif "bytes" in msg:
                os.write(master_fd, msg["bytes"])
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        read_task.cancel()
        try:
            os.kill(child_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            os.close(master_fd)
        except OSError:
            pass
        active_ptys.pop(terminal_id, None)


@app.websocket("/ws/reviews")
async def reviews_ws(websocket: WebSocket):
    await websocket.accept()
    last_count = 0
    try:
        while True:
            await asyncio.sleep(1)
            if STATE["session"]:
                current_count = STATE["session"].total_reviews
                if current_count > last_count:
                    last_count = current_count
                    data = {
                        "reviews": [r.to_dict() for r in STATE["session"].reviews[-20:]],
                        "stats": {
                            "total": STATE["session"].total_reviews,
                            "issues": STATE["session"].total_issues,
                            "avg_score": round(STATE["session"].avg_score, 1),
                            "duration": STATE["session"].session_duration,
                            "scores": STATE["session"].score_history[-20:],
                            "hot_files": STATE["session"].hot_files(5),
                            "recurring": STATE["session"].recurring_issues(5),
                        },
                    }
                    await websocket.send_text(json.dumps(data))
    except WebSocketDisconnect:
        pass


@app.get("/api/budget")
async def get_budget():
    return token_budget.usage


@app.get("/api/chat/history")
async def get_chat_history():
    if STATE["session"]:
        return {"messages": STATE["session"].chat_history[-50:]}
    return {"messages": []}


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        return JSONResponse({"error": "Empty message"}, status_code=400)
    if len(message) > 2000:
        return JSONResponse({"error": "Message too long (max 2000 chars)"}, status_code=400)

    project_dir = STATE["project_dir"] or os.getcwd()

    # Save user message
    if STATE["session"]:
        STATE["session"].add_chat("user", message)

    # Run in thread to not block event loop
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, run_codex_chat, project_dir, message)

    # Save assistant response
    if STATE["session"]:
        STATE["session"].add_chat("assistant", response)

    return {"response": response, "budget": token_budget.usage}


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def on_review(review):
    STATE["reviews"].append(review)


def start_server(project_dir=None, port=7777, mode="standard"):
    config = load_config(project_dir)
    config.review.depth = mode
    codeshock_dir = init_codeshock_dir(project_dir)
    config.codeshock_dir = str(codeshock_dir)

    sync_context(config)

    session = SessionManager(config.codeshock_dir)

    STATE["config"] = config
    STATE["session"] = session
    STATE["project_dir"] = config.project_dir

    watcher = CodeshockWatcher(config, session, on_review)
    watcher.start()
    STATE["watcher"] = watcher

    # Re-sync context every 5 minutes so AGENTS.md stays fresh
    def periodic_sync():
        while True:
            time.sleep(300)
            try:
                sync_context(config)
            except Exception:
                pass

    sync_thread = threading.Thread(target=periodic_sync, daemon=True)
    sync_thread.start()

    print(f"codeshock v1.1.0")
    print(f"Project: {config.project_dir}")
    print(f"Mode: {mode}")
    print(f"")
    print(f"Open in browser: http://localhost:{port}")
    print(f"")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
