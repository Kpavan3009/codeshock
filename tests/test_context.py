import tempfile
from pathlib import Path

from claudex.config import ClaudexConfig, GeneralConfig, ReviewConfig, DisplayConfig
from claudex.context import build_agents_md


def make_config(tmpdir):
    claudex_dir = Path(tmpdir) / ".claudex"
    claudex_dir.mkdir(exist_ok=True)
    return ClaudexConfig(
        project_dir=str(tmpdir),
        claudex_dir=str(claudex_dir),
    )


def test_build_agents_md_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".git").mkdir()
        config = make_config(tmpdir)
        result = build_agents_md(config)
        assert "REVIEWER" in result
        assert "VERDICT" in result


def test_build_agents_md_with_project_claude_md():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".git").mkdir()
        claude_dir = Path(tmpdir) / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text("Use TypeScript. Always write tests.")

        config = make_config(tmpdir)
        result = build_agents_md(config)
        assert "TypeScript" in result


def test_build_agents_md_with_tasks():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / ".git").mkdir()
        tasks_dir = Path(tmpdir) / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "todo.md").write_text("- [ ] Fix auth bug\n- [x] Add logging")

        config = make_config(tmpdir)
        result = build_agents_md(config)
        assert "Fix auth bug" in result
