# codeshock

Your AI writes code. Who reviews it?

codeshock puts a second brain next to your primary coding agent. Claude Code generates, Codex reviews, and you see everything side by side in your browser. No copy-pasting between tools, no manual review triggers. You code, it watches.

## What this actually does

You run `codeshock` in a project directory. It opens a web interface in your browser:

- **Left panel**: A full Claude Code terminal session. Type prompts, write code, commit, push. Everything you normally do.
- **Right panel**: A live review dashboard. Every time you save a file, commit, or push, Codex automatically reviews the diff and shows the results in real time.

Both tools share the same project context. Your CLAUDE.md, your primer, your skills, your lessons, your TODOs, your git history. codeshock reads all of it and translates it into an AGENTS.md that Codex understands natively. Same knowledge, different engine.

The left panel is a real terminal session rendered with xterm.js. Full color, cursor, scrolling, input. Claude Code runs exactly as it would in your native terminal. The right panel is a structured review dashboard with score trends, hot file tracking, and recurring issue detection.

## Setup

You need two things installed and authenticated:

1. [Claude Code](https://claude.ai/download)
2. [Codex CLI](https://github.com/openai/codex): `npm i -g @openai/codex`

Then:

```bash
pip install codeshock
```

## Usage

```bash
codeshock
```

That's it. Your browser opens with the full interface.

```bash
codeshock -p /path/to/project       # Specify project directory
codeshock -m paranoid                # Deep security review mode
codeshock --port 9000                # Custom port
codeshock --no-browser               # Don't auto-open browser
```

### Review modes

```bash
codeshock -m quick       # Fast surface scan
codeshock -m standard    # Default balanced review
codeshock -m thorough    # Deep security + logic review
codeshock -m paranoid    # OWASP, race conditions, edge cases
codeshock -m learn       # Reviews include explanations
```

### Other commands

```bash
codeshock sync            # Rebuild AGENTS.md from your Claude Code context
codeshock reviews         # View past reviews in terminal
codeshock stats           # Aggregate stats across sessions
codeshock export          # Export reviews as markdown report
codeshock export -f json  # Export as JSON
codeshock init            # Initialize .codeshock/ config in project
```

## How the context sync works

This is what makes codeshock different from running two terminals side by side. When you launch codeshock, it reads:

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

**On git commit**: captures the commit diff, reviews immediately.

**On git push**: full thorough review before code hits remote.

Reviews appear in the right panel as structured cards with verdict, score, file references, and line numbers.

## The web interface

The browser interface has:

- Full xterm.js terminal for Claude Code (left panel, resizable)
- Live review dashboard (right panel) with:
  - Session stats: avg score, total reviews, total issues
  - Score trend sparkline
  - Review cards with verdict badges (clean/minor/issues/critical), file names, issue descriptions, and 10-point score bars
  - Hot files heatmap showing most-reviewed files
  - Recurring issues tracker
- Top bar with live session stats and watching indicator
- Bottom bar with review mode selector
- Draggable divider to resize panels

Everything updates in real time via WebSocket.

## Configuration

Run `codeshock init` to create `.codeshock/config.toml` in your project:

```toml
[general]
debounce_seconds = 3
review_on_save = true
review_on_commit = true
review_on_push = true

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

### Focus mode

Tell Codex to focus on a specific concern:

```toml
focus = ["security", "SQL injection"]
```

## Architecture

```
Browser (localhost:7777)
  |
  |-- WebSocket /ws/terminal/claude  -->  PTY process (claude CLI)
  |-- WebSocket /ws/reviews          -->  Live review feed
  |-- GET /api/reviews               -->  Review history + stats
  |
FastAPI server (Python)
  |
  |-- File watcher (watchdog)        -->  Detects changes
  |-- Reviewer (codex exec)          -->  Runs Codex reviews
  |-- Context sync                   -->  CLAUDE.md -> AGENTS.md
  |-- Session manager                -->  Persistence + analytics
```

## Requirements

- Python 3.10+
- Claude Code CLI (authenticated)
- Codex CLI (authenticated)
- macOS or Linux (Windows via WSL)

## How it compares

There are other multi-agent orchestrators out there. Most of them are platforms with dozens of commands or desktop apps with subscription tiers. codeshock is one command. It does one thing: puts an intelligent reviewer next to your coding agent with shared context and zero setup.

No frameworks. No agent swarms. No 50-command plugin systems. Just a watcher, a reviewer, and a browser.

## License

MIT
