# codeshock

Your AI writes code. **codeshock reviews it in real time.**

Claude Code generates. Codex reviews. You see everything side by side in your browser. No copy-pasting, no manual reviews. You code, it watches.

## What it does

Run `codeshock` in any project. A browser dashboard opens:

- **Left** — Full Claude Code terminal. Write code, commit, push. Everything you normally do.
- **Right** — Live Codex review panel. Every save, commit, or push triggers an automatic code review with real thoughts, issues, suggestions, and a score.

Both tools share full project context. Same codebase knowledge, different AI engines reviewing your work.

## Features

- **Auto-reviews on save/commit/push** — no manual triggers needed
- **Real thoughts, not just scores** — Codex shares genuine opinions on your code like a real reviewer
- **Suggestions with Discuss** — get improvement ideas, click Discuss to chat about any of them
- **Built-in Codex chat** — ask questions about your code directly in the Chat tab
- **Budget protection** — tracks API calls per hour/session, warns before limits, prevents surprise bills
- **Session persistence** — close your laptop, reopen tomorrow, all reviews and chat history are still there
- **5 review modes** — quick, standard, thorough, paranoid, learn
- **Score trends + hot files** — see which files get flagged most, track quality over time
- **Shared context sync** — reads your CLAUDE.md, primer, skills, git history and compiles it into AGENTS.md for Codex
- **Concurrency safe** — no API 400 errors from overlapping requests
- **Works alongside Claude Code Mac app** — both run independently, no conflicts

## Install

Prerequisites:
- [Claude Code CLI](https://claude.ai/download) (authenticated)
- [Codex CLI](https://github.com/openai/codex): `npm i -g @openai/codex` (authenticated)
- Python 3.10+

```bash
pip install codeshock
```

## Usage

```bash
codeshock                            # Launch in current directory
codeshock -p /path/to/project        # Specify project
codeshock -m paranoid                # Deep security review mode
codeshock --port 9000                # Custom port
codeshock --no-browser               # Don't auto-open browser
```

### Review modes

| Mode | What it does |
|------|-------------|
| `quick` | Fast surface scan, first impressions |
| `standard` | Balanced review (default) |
| `thorough` | Security + logic deep dive |
| `paranoid` | OWASP, race conditions, edge cases |
| `learn` | Reviews include explanations and teaching |

### Other commands

```bash
codeshock sync       # Rebuild AGENTS.md from your Claude Code context
codeshock reviews    # View past reviews in terminal
codeshock stats      # Session stats
codeshock export     # Export reviews as markdown
codeshock init       # Initialize config in project
```

## How it works

```
Browser (localhost:7777)
  |
  |-- Claude Code terminal (left)   Full PTY via xterm.js
  |-- Review dashboard (right)      Live reviews via WebSocket
  |-- Chat panel (right tab)        Talk to Codex about your code
  |
  |-- File watcher                  Detects saves/commits/pushes
  |-- Codex reviewer                Reviews diffs automatically
  |-- Context sync                  CLAUDE.md -> AGENTS.md
  |-- Session persistence           Reviews + chat saved across restarts
  |-- Budget tracker                Rate limits API calls
```

## Configuration

Run `codeshock init` to create `.codeshock/config.toml`:

```toml
[general]
debounce_seconds = 3
review_on_save = true
review_on_commit = true
review_on_push = true

[review]
depth = "standard"
focus = []
ignore_patterns = ["*.md", "*.csv", "*.lock", ".git/*", "node_modules/*"]
priority_files = ["auth.js", "api.js"]
```

## Requirements

- Python 3.10+
- Claude Code CLI (authenticated)
- Codex CLI (authenticated)
- macOS or Linux (Windows via WSL)

## License

MIT
