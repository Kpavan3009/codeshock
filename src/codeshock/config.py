import os
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib as tomli
else:
    import tomli
from dataclasses import dataclass, field
from typing import List, Optional


DEFAULT_CONFIG = {
    "general": {
        "debounce_seconds": 3,
        "review_on_save": True,
        "review_on_commit": True,
        "review_on_push": True,
        "pane_ratio": "70:30",
    },
    "review": {
        "depth": "standard",
        "focus": [],
        "ignore_patterns": [
            "*.md", "*.txt", "*.csv", "*.json", "*.lock",
            "*.png", "*.jpg", "*.gif", "*.svg", "*.ico",
            ".codeshock/*", ".git/*", "node_modules/*", "__pycache__/*",
            ".env", ".env.*",
        ],
        "priority_files": [],
    },
    "display": {
        "show_score": True,
        "show_diff_preview": True,
        "show_trends": True,
        "show_hotfiles": True,
    },
}


@dataclass
class ReviewConfig:
    depth: str = "standard"
    focus: List[str] = field(default_factory=list)
    ignore_patterns: List[str] = field(default_factory=lambda: DEFAULT_CONFIG["review"]["ignore_patterns"][:])
    priority_files: List[str] = field(default_factory=list)


@dataclass
class DisplayConfig:
    show_score: bool = True
    show_diff_preview: bool = True
    show_trends: bool = True
    show_hotfiles: bool = True


@dataclass
class GeneralConfig:
    debounce_seconds: int = 3
    review_on_save: bool = True
    review_on_commit: bool = True
    review_on_push: bool = True
    pane_ratio: str = "70:30"


@dataclass
class CodeshockConfig:
    general: GeneralConfig = field(default_factory=GeneralConfig)
    review: ReviewConfig = field(default_factory=ReviewConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    project_dir: str = ""
    codeshock_dir: str = ""


def find_project_root(start_dir: Optional[str] = None) -> Path:
    current = Path(start_dir or os.getcwd()).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path(start_dir or os.getcwd()).resolve()


def load_config(project_dir: Optional[str] = None) -> CodeshockConfig:
    root = find_project_root(project_dir)
    codeshock_dir = root / ".codeshock"
    config_path = codeshock_dir / "config.toml"

    config = CodeshockConfig(
        project_dir=str(root),
        codeshock_dir=str(codeshock_dir),
    )

    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomli.load(f)

        if "general" in data:
            for k, v in data["general"].items():
                if hasattr(config.general, k):
                    setattr(config.general, k, v)

        if "review" in data:
            for k, v in data["review"].items():
                if hasattr(config.review, k):
                    setattr(config.review, k, v)

        if "display" in data:
            for k, v in data["display"].items():
                if hasattr(config.display, k):
                    setattr(config.display, k, v)

    return config


def init_codeshock_dir(project_dir: Optional[str] = None) -> Path:
    root = find_project_root(project_dir)
    codeshock_dir = root / ".codeshock"
    codeshock_dir.mkdir(exist_ok=True)
    (codeshock_dir / "reviews").mkdir(exist_ok=True)
    (codeshock_dir / "queue").mkdir(exist_ok=True)

    config_path = codeshock_dir / "config.toml"
    if not config_path.exists():
        config_path.write_text(generate_default_config())

    gitignore = codeshock_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("session.jsonl\nqueue/\nreviews/\nagents.md.generated\n")

    return codeshock_dir


def generate_default_config() -> str:
    return """[general]
debounce_seconds = 3
review_on_save = true
review_on_commit = true
review_on_push = true
pane_ratio = "70:30"

[review]
depth = "standard"
focus = []
ignore_patterns = [
    "*.md", "*.txt", "*.csv", "*.json", "*.lock",
    "*.png", "*.jpg", "*.gif", "*.svg", "*.ico",
    ".codeshock/*", ".git/*", "node_modules/*", "__pycache__/*",
    ".env", ".env.*",
]
priority_files = []

[display]
show_score = true
show_diff_preview = true
show_trends = true
show_hotfiles = true
"""
