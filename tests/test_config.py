import os
import tempfile
from pathlib import Path

from codeshock.config import load_config, init_codeshock_dir, find_project_root


def test_find_project_root_with_git():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".git").mkdir()
        root = find_project_root(tmpdir)
        assert root == Path(tmpdir).resolve()


def test_find_project_root_without_git():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = find_project_root(tmpdir)
        assert root == Path(tmpdir).resolve()


def test_init_codeshock_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".git").mkdir()
        codeshock_dir = init_codeshock_dir(tmpdir)
        assert codeshock_dir.exists()
        assert (codeshock_dir / "config.toml").exists()
        assert (codeshock_dir / "reviews").exists()
        assert (codeshock_dir / "queue").exists()
        assert (codeshock_dir / ".gitignore").exists()


def test_load_config_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".git").mkdir()
        config = load_config(tmpdir)
        assert config.general.debounce_seconds == 3
        assert config.general.review_on_save is True
        assert config.review.depth == "standard"
        assert config.display.show_score is True
