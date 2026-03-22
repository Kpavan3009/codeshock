# codeshock

Your AI writes code. Who's reviewing it? Another AI.

codeshock is a browser dashboard that pairs **Claude Code** (your coding agent) with **Codex** (your reviewer). You code on the left, Codex watches everything on the right. Every prompt you give Claude, every response it generates, every file save, every commit, every push. Codex reads it all and gives you its honest, unbiased take in real time.

Two AI engines. Two perspectives. One screen.

```bash
codeshock
```

Browser opens. Start coding. Codex is already watching.

## How it compares

| Feature | Claude Squad | Octopus | 1Code | Kodo | Aider | codeshock |
|---------|:-----------:|:-------:|:-----:|:----:|:-----:|:---------:|
| One-command start | Yes | No | No | No | Yes | **Yes** |
| Auto context sync (CLAUDE.md to AGENTS.md) | No | No | No | No | No | **Yes** |
| Live review of every Claude interaction | No | No | No | No | No | **Yes** |
| Live review on file save/commit/push | No | No | No | No | No | **Yes** |
| Honest, unbiased review thoughts | No | No | No | No | No | **Yes** |
| Suggestions you can discuss in chat | No | No | No | No | No | **Yes** |
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

Browser opens automatically. Claude Code on the left, Codex reviews on the right.

Want to make it even faster? Add this to your `.zshrc` or `.bashrc`:

```bash
alias shock='source ~/claudex/.venv/bin/activate && codeshock -p ~/your-project --port 7777'
```

Now every morning after booting your laptop, open terminal and type:

```bash
shock
```

That's your entire workflow. One word.

## What actually happens

**Codex watches everything you do in Claude Code.** Not just file saves. Every prompt you type, every response Claude gives, Codex reads it and forms its own opinion.

When Claude finishes responding, Codex reviews the exchange and shows:
- A verdict badge (clean, minor, issues, critical)
- Its honest thoughts. Not polite AI fluff. Real opinions from a different model with a different perspective. If Claude gave bad advice, Codex calls it out.
- Specific issues with file names and line numbers
- Suggestions for what could be done better, each with a **Discuss** button
- A score out of 10. Honest scoring. 5 is average. Most code is average.

On top of that, file saves, commits, and pushes also trigger separate code diff reviews.

**Click Discuss** on any suggestion and it opens the Chat tab pre-loaded with context. Ask Codex to explain more, show you how to implement it, or debate whether it's worth doing.

**Session persistence** means you can close your laptop, come back tomorrow, and all your reviews and chat history are still there.

**Budget bar** at the top tracks your API usage. Goes yellow at 50%, red at 80%, blocks at 100%. No surprise bills. Codex uses your ChatGPT subscription, Claude uses your Anthropic account. No extra API keys.

## Review modes

```bash
codeshock -m quick      # Fast gut check, first impressions
codeshock -m standard   # Balanced review (default)
codeshock -m thorough   # Security audit, zero tolerance
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
- Full project context is shared. CLAUDE.md, memory files, git history, skills, chat history, everything. Both AIs know what's going on.
- Context auto-refreshes every 5 minutes so nothing goes stale.

## Requirements

- Python 3.10+
- Claude Code CLI (authenticated)
- Codex CLI (authenticated)
- macOS or Linux (Windows via WSL)

## License

MIT
