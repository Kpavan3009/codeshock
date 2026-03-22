# codeshock

Your AI writes code. Who's reviewing it? Another AI.

codeshock is a browser-based dashboard that pairs **Claude Code** (your coding agent) with **Codex** (your reviewer). You code on the left, reviews show up on the right. Every file save, every commit, every push gets reviewed automatically. No setup, no config files, no extra tabs.

One command. That's it.

```bash
codeshock
```

Browser opens. Claude Code terminal on the left. Live review panel on the right. Start coding.

## How it compares

| Feature | Claude Squad | Octopus | 1Code | Kodo | Aider | codeshock |
|---------|:-----------:|:-------:|:-----:|:----:|:-----:|:---------:|
| One-command start | Yes | No | No | No | Yes | **Yes** |
| Auto context sync (CLAUDE.md to AGENTS.md) | No | No | No | No | No | **Yes** |
| Live review on file save | No | No | No | No | No | **Yes** |
| Conversational review thoughts | No | No | No | No | No | **Yes** |
| Suggestions you can discuss | No | No | No | No | No | **Yes** |
| Built-in chat with reviewer | No | No | No | No | No | **Yes** |
| Score trend tracking | No | No | No | No | No | **Yes** |
| Recurring issue detection | No | No | No | Partial | No | **Yes** |
| Hot file heatmap | No | No | No | No | No | **Yes** |
| Review export (md/json) | No | No | No | No | No | **Yes** |
| Focus mode (security, perf, etc) | No | No | No | No | No | **Yes** |
| Session persistence across restarts | No | Yes | No | No | No | **Yes** |
| Budget protection (rate limits) | No | No | No | No | No | **Yes** |
| Zero config required | No | No | No | No | Yes | **Yes** |

## Install

You need three things:

1. **Python 3.10+**
2. **Claude Code CLI** - [download here](https://claude.ai/download), sign in
3. **Codex CLI** - `npm i -g @openai/codex`, sign in

Then:

```bash
pip install codeshock
```

Done.

## Daily usage

First time:

```bash
codeshock -p ~/your-project
```

Browser opens automatically. Claude Code on the left, reviews on the right.

Want to make it even faster? Add this to your `.zshrc`:

```bash
alias shock='source ~/claudex/.venv/bin/activate && codeshock -p ~/your-project --port 7777'
```

Now every morning after booting your laptop, open terminal and type:

```bash
shock
```

That's your entire workflow. One word.

## What you actually see

**Review cards** show up every time you save a file:
- A verdict badge (clean, minor, issues, critical)
- Real thoughts from Codex, not generic AI fluff. It tells you what it actually thinks about your code.
- Specific issues with file names and line numbers
- Suggestions for what could be better, each with a **Discuss** button
- A score out of 10 with a visual bar

**Click Discuss** on any suggestion and it opens the Chat tab with that suggestion pre-loaded. Ask Codex to explain more, show you how to implement it, or debate whether it's worth doing. It's like having a senior dev sitting next to you.

**Session persistence** means you can close your laptop, come back tomorrow, and all your reviews and chat history are still there. Nothing gets lost.

**Budget bar** at the top tracks your API usage. Goes yellow at 50%, red at 80%, blocks at 100%. You'll never get a surprise bill.

## Review modes

```bash
codeshock -m quick      # Fast scan, first impressions only
codeshock -m standard   # Balanced review (default)
codeshock -m thorough   # Deep security and logic review
codeshock -m paranoid   # Everything. OWASP, race conditions, edge cases.
codeshock -m learn      # Explains WHY each issue matters and HOW to fix it
```

## More commands

```bash
codeshock sync       # Rebuild AGENTS.md from your Claude Code context
codeshock reviews    # See past reviews in your terminal
codeshock stats      # Session stats (avg score, total issues, hot files)
codeshock export     # Export all reviews as markdown
codeshock export -f json   # Export as JSON
codeshock init       # Create config file for custom settings
```

## Configuration (optional)

Run `codeshock init` to tweak settings. Works fine without it.

```toml
[review]
depth = "standard"
focus = ["security"]                    # Focus reviews on specific concerns
priority_files = ["auth.js", "api.js"]  # Flag files that need extra scrutiny

[general]
debounce_seconds = 3
review_on_save = true
review_on_commit = true
review_on_push = true
```

## Works with your existing setup

- Claude Code Mac app and the embedded terminal run independently. Use both at the same time, no conflicts.
- Codex uses your ChatGPT subscription. No separate API key needed.
- Claude Code uses your Anthropic account. Same deal.
- Both read the same project context (CLAUDE.md, git history, skills, etc).

## Requirements

- Python 3.10+
- Claude Code CLI (authenticated)
- Codex CLI (authenticated)
- macOS or Linux (Windows via WSL)

## License

MIT
