import fnmatch
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from .config import CodeshockConfig
from .reviewer import get_git_diff, get_commit_diff, run_codex_review
from .session import SessionManager


class DebouncedHandler(FileSystemEventHandler):
    def __init__(self, config: CodeshockConfig, session: SessionManager, on_review: Callable):
        super().__init__()
        self.config = config
        self.session = session
        self.on_review = on_review
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._last_commit = ""
        self._reviewing = False

    def _should_ignore(self, path: str) -> bool:
        rel_path = os.path.relpath(path, self.config.project_dir)
        for pattern in self.config.review.ignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            if fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
        if ".codeshock" in rel_path or ".git" in rel_path.split(os.sep):
            return True
        return False

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        self._schedule_review("save")

    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if self._should_ignore(event.src_path):
            return
        self._schedule_review("save")

    def _schedule_review(self, trigger: str):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(
                self.config.general.debounce_seconds,
                self._run_review,
                args=[trigger],
            )
            self._timer.daemon = True
            self._timer.start()

    def _run_review(self, trigger: str):
        if self._reviewing:
            return
        self._reviewing = True
        try:
            diff = get_git_diff(self.config.project_dir)
            if not diff.strip():
                diff = get_git_diff(self.config.project_dir, staged=True)
            if not diff.strip():
                return

            review = run_codex_review(self.config, diff, trigger)
            if review:
                self.session.add_review(review)
                self.on_review(review)
        finally:
            self._reviewing = False


class GitCommitWatcher(threading.Thread):
    def __init__(self, config: CodeshockConfig, session: SessionManager, on_review: Callable):
        super().__init__(daemon=True)
        self.config = config
        self.session = session
        self.on_review = on_review
        self._stop_event = threading.Event()
        self._last_commit = self._get_head()
        self._reviewing = False

    def _get_head(self) -> str:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True,
                cwd=self.config.project_dir, timeout=5,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _get_push_status(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "status", "-sb"],
                capture_output=True, text=True,
                cwd=self.config.project_dir, timeout=5,
            )
            return "ahead" not in result.stdout
        except Exception:
            return True

    def run(self):
        was_pushed = self._get_push_status()

        while not self._stop_event.is_set():
            time.sleep(2)

            current_head = self._get_head()
            if current_head and current_head != self._last_commit:
                self._last_commit = current_head
                if self.config.general.review_on_commit and not self._reviewing:
                    self._reviewing = True
                    try:
                        diff = get_commit_diff(self.config.project_dir)
                        if diff:
                            review = run_codex_review(self.config, diff, "commit")
                            if review:
                                self.session.add_review(review)
                                self.on_review(review)
                    finally:
                        self._reviewing = False

            is_pushed = self._get_push_status()
            if was_pushed and not is_pushed:
                pass
            elif not was_pushed and is_pushed and self.config.general.review_on_push:
                if not self._reviewing:
                    self._reviewing = True
                    try:
                        diff = get_commit_diff(self.config.project_dir)
                        if diff:
                            review = run_codex_review(self.config, diff, "push")
                            if review:
                                self.session.add_review(review)
                                self.on_review(review)
                    finally:
                        self._reviewing = False
            was_pushed = is_pushed

    def stop(self):
        self._stop_event.set()


class CodeshockWatcher:
    def __init__(self, config: CodeshockConfig, session: SessionManager, on_review: Callable):
        self.config = config
        self.session = session
        self.on_review = on_review
        self._observer: Optional[Observer] = None
        self._commit_watcher: Optional[GitCommitWatcher] = None

    def start(self):
        handler = DebouncedHandler(self.config, self.session, self.on_review)
        self._observer = Observer()
        self._observer.schedule(handler, self.config.project_dir, recursive=True)
        self._observer.daemon = True
        self._observer.start()

        self._commit_watcher = GitCommitWatcher(self.config, self.session, self.on_review)
        self._commit_watcher.start()

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
        if self._commit_watcher:
            self._commit_watcher.stop()
            self._commit_watcher.join(timeout=5)
