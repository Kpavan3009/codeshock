# codeshock

Your AI writes code. Who reviews it?

codeshock puts a second brain next to your primary coding agent. Claude Code generates, Codex reviews, and you see everything in a split terminal with a live review dashboard. No copy-pasting between tools, no manual review triggers. You code, it watches.

## What this actually does

You run `codeshock` in a project directory. It opens a split terminal:

- **Left (70%)**: Claude Code. Your workspace. Nothing changes about how you work.
- **Right (30%)**: A live review dashboard. Every time you save a file, commit, or push, Codex automatically reviews the diff and shows results here.

Both tools share the same project context. Your CLAUDE.md, your primer, your skills, your lessons, your TODOs, your git history. codeshock reads all of it and translates it into an AGENTS.md that Codex understands natively. Same knowledge, different engine.

```
+-------------------------------------+----------------------+
|                                     | REVIEW DASHBOARD     |
|    CLAUDE CODE                      |                      |
|                                     | Session: 1h 23m      |
|    Your full workspace.             | Reviews: 12          |
|    Work like you normally do.       | Avg score: 8.4/10    |
|                                     |                      |
|                                     | LATEST               |
|                                     | >> auth.js     7/10  |
|                                     |    XSS risk ln:34    |
|                                     |                      |
|                                     | . utils.js    10/10  |
|                                     |    Clean             |
|                                     |                      |
|                                     | >> api.js      6/10  |
|                                     |    No rate limit     |
|                                     |                      |
|                                     | HOT FILES            |
|                                     |  auth.js ####. 12    |
|                                     |  data.js ##... 6     |
|                                     |                      |
|                                     | TRENDS               |
|                                     |  Score: going up     |
|                                     |                      |
|                                     | RECURRING            |
|                                     |  1. Missing input    |
|                                     |     validation (3x)  |
+-------------------------------------+----------------------+
| codeshock v1.0 | Watching | Last: 8s ago | Score: 8.4        |
+----------------------------------------------------------+
```

## Setup

You need three things installed:

1. [Claude Code](https://claude.ai/download) (authenticated)
2. [Codex CLI](https://github.com/openai/codex) (authenticated): `npm i -g @openai/codex`
3. [tmux](https://github.com/tmux/tmux): `brew install tmux` (mac) or `apt install tmux` (linux)

Then:

```bash
pip install codeshock
```

## Usage

```bash
# Start in current directory
codeshock

# Start in a specific project
codeshock -p /path/to/project

# Review modes
codeshock -m quick       # Fast surface scan
codeshock -m standard    # Default balanced review
codeshock -m thorough    # Deep security + logic review
codeshock -m paranoid    # Everything. OWASP, race conditions, edge cases.
codeshock -m learn       # Reviews include explanations (good for learning)
```

### Commands

```bash
codeshock              # Launch split terminal with live reviews
codeshock sync         # Rebuild AGENTS.md from your Claude Code context
codeshock reviews      # View past reviews in terminal
codeshock stats        # Aggregate stats across sessions
codeshock export       # Export reviews as markdown report
codeshock export -f json  # Export as JSON
codeshock init         # Initialize .codeshock/ config in project
```

### Keyboard shortcuts (in the review panel)

| Key | Action |
|-----|--------|
| `d` | Expand detail on selected review |
| `h` | Show full review history |
| `f` | Set focus mode (e.g. "focus on SQL injection") |
| `p` | Pause/resume auto-review |
| `q` | Quit review panel |

## How the context sync works

This is the part that matters. When you launch codeshock, it reads:

- `~/.claude/CLAUDE.md` (your global preferences)
- `~/.claude/primer.md` (your current state)
- `.claude/CLAUDE.md` (project-level instructions)
- `tasks/lessons.md` (what you've learned)
- `tasks/todo.md` (what you're working on)
- All installed Claude Code skills (summarized)
- Recent git log (last 15 commits)
- Previous session summary (if any)

It compiles all of this into a single `AGENTS.md` at your project root. Codex reads AGENTS.md natively, the same way Claude Code reads CLAUDE.md. So when Codex reviews your code, it knows your project architecture, your coding standards, what you've been working on, and what mistakes you've made before.

Every time you launch codeshock, it rebuilds this file. The context is always current.

## How auto-review works

A background daemon watches your project directory.

**On file save** (debounced 3 seconds): captures `git diff`, sends to Codex for review.

**On git commit**: captures the commit diff, sends for review immediately.

**On git push**: full thorough review before code hits remote.

Reviews appear in the right panel as structured cards with verdict, score, file references, and line numbers. No raw terminal output to parse.

## Configuration

Run `codeshock init` to create `.codeshock/config.toml` in your project:

```toml
[general]
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
```

### Priority files

Flag files that need extra scrutiny:

```toml
priority_files = ["auth.js", "api.js", "middleware.js"]
```

These get thorough reviews even when the global mode is set to quick.

### Focus mode

Tell Codex to focus on a specific concern:

```toml
focus = ["security", "SQL injection"]
```

Or press `f` in the review panel to set focus on the fly.

## What gets stored

```
.codeshock/
  config.toml            # Your preferences
  session.jsonl           # Full session log
  session-summary.md      # Summary for next session
  agents.md.generated     # Generated AGENTS.md (for reference)
  reviews/                # Individual review JSONs
  queue/                  # Pending review diffs
```

The `.codeshock/.gitignore` excludes session data and reviews from git by default. The AGENTS.md at your project root is also auto-generated and should be gitignored.

## Project structure

```
codeshock/
  pyproject.toml
  README.md
  LICENSE
  .gitignore
  src/
    codeshock/
      __init__.py
      __main__.py
      cli.py            # Entry point and commands
      launcher.py       # tmux session management
      watcher.py        # File system watcher + git monitor
      reviewer.py       # Diff capture, Codex execution, output parsing
      context.py        # CLAUDE.md to AGENTS.md sync engine
      session.py        # Session log, stats, recurring issues
      display.py        # Rich terminal dashboard
      config.py         # Config loading and defaults
```

## Requirements

- Python 3.10+
- Claude Code CLI (authenticated)
- Codex CLI (authenticated)
- tmux
- macOS or Linux (Windows via WSL)

## How it compares

There are other multi-agent orchestrators out there. Most of them are platforms with dozens of commands or desktop apps with subscription tiers. codeshock is one command. It does one thing: puts an intelligent reviewer next to your coding agent with shared context and zero setup.

No frameworks. No agent swarms. No 50-command plugin systems. Just a watcher, a reviewer, and a dashboard.

## License

MIT
