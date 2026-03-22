import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import CodeshockConfig
from .session import ReviewRecord

# Concurrency lock — only one codex call at a time to prevent API 400 errors
_codex_lock = threading.Lock()


REVIEW_PROMPT_TEMPLATE = """You are an independent code reviewer with zero bias. Review this diff like a real human would. Not a polite AI. A real engineer who has opinions and isn't afraid to share them.

Rules:
- Rate honestly. 5 is average. Don't inflate scores. Only give 8+ if it's genuinely impressive.
- If something is wrong, say it directly. Don't soften it.
- If it's good, say that too. Don't nitpick for the sake of it.
- Think about: correctness, security, performance, readability, edge cases.

Changed files: {files}

```diff
{diff}
```

Respond in this format:
VERDICT: [clean|minor|issues|critical]
THOUGHTS: 3-5 sentences. Your unfiltered take. What would you actually say in a real code review? Be specific, reference actual code.
ISSUES:
1. file:line - description
SUGGESTIONS:
1. The best improvement they could make right now (specific and actionable)
2. Another if relevant
SCORE: X/10
SUMMARY: one line, honest
"""

THOROUGH_PROMPT_TEMPLATE = """You are a security auditor with zero tolerance for BS. Check for SQL injection, XSS, CSRF, auth gaps, race conditions, logic errors, hardcoded secrets. Be brutally honest.

Changed files: {files}

```diff
{diff}
```

Respond in this format:
VERDICT: [clean|minor|issues|critical]
THOUGHTS: 3-5 sentences. What worries you? What's actually solid? Don't sugarcoat. Rate honestly, 5 is average.
ISSUES:
1. file:line - description
SUGGESTIONS:
1. Most important hardening or improvement
2. Second priority if relevant
SCORE: X/10
SUMMARY: one line, honest
"""

QUICK_PROMPT_TEMPLATE = """Quick gut check. First impression only. Be honest, don't be nice.

Changed files: {files}

```diff
{diff}
```

VERDICT: [clean|minor|issues|critical]
THOUGHTS: 1-2 sentences. Gut reaction. No filler.
ISSUES: (numbered list or "none")
SUGGESTIONS: (1-2 quick wins, or "none")
SCORE: X/10
SUMMARY: one line
"""

LEARN_PROMPT_TEMPLATE = """You're mentoring a developer. Be honest but constructive. Explain your thinking like you're pair programming. For each issue, explain why it actually matters in the real world.

Changed files: {files}

```diff
{diff}
```

VERDICT: [clean|minor|issues|critical]
THOUGHTS: 3-5 sentences. What should this developer take away? Be honest about skill level you see. Rate fairly, 5 is average.
ISSUES:
1. file:line - description
   WHY: real-world explanation
   FIX: specific suggestion
SUGGESTIONS:
1. The most valuable thing they could learn from this code
2. Another if relevant
SCORE: X/10
SUMMARY: one line
"""


def get_prompt_template(depth: str) -> str:
    templates = {
        "quick": QUICK_PROMPT_TEMPLATE,
        "standard": REVIEW_PROMPT_TEMPLATE,
        "thorough": THOROUGH_PROMPT_TEMPLATE,
        "paranoid": THOROUGH_PROMPT_TEMPLATE,
        "learn": LEARN_PROMPT_TEMPLATE,
    }
    return templates.get(depth, REVIEW_PROMPT_TEMPLATE)


def get_git_diff(project_dir: str, staged: bool = False) -> str:
    cmd = ["git", "diff"]
    if staged:
        cmd.append("--staged")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=project_dir, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_commit_diff(project_dir: str, commit: str = "HEAD") -> str:
    try:
        result = subprocess.run(
            ["git", "show", "--stat", "--patch", commit],
            capture_output=True, text=True, cwd=project_dir, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_changed_files(diff: str) -> List[str]:
    files = []
    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            parts = line.split(" b/")
            if len(parts) > 1:
                files.append(parts[-1])
        elif line.startswith("+++ b/"):
            files.append(line[6:])
    return list(set(files))


def parse_review_output(output: str) -> Dict:
    verdict = "unknown"
    score = 0
    issues = []
    summary = ""
    thoughts = ""

    verdict_match = re.search(r"VERDICT:\s*(clean|minor|issues|critical)", output, re.IGNORECASE)
    if verdict_match:
        verdict = verdict_match.group(1).lower()

    thoughts_match = re.search(r"THOUGHTS:\s*(.+?)(?:\nISSUES:|\nSUGGESTIONS:|\nSCORE:|\nSUMMARY:|\nVERDICT:|\Z)", output, re.DOTALL | re.IGNORECASE)
    if thoughts_match:
        thoughts = thoughts_match.group(1).strip()

    score_match = re.search(r"SCORE:\s*(\d+)/10", output)
    if score_match:
        score = int(score_match.group(1))

    summary_match = re.search(r"SUMMARY:\s*(.+?)(?:\n|$)", output)
    if summary_match:
        summary = summary_match.group(1).strip()

    issue_pattern = re.compile(r"(\d+)\.\s+([^\s]+?):?(\d*)\s*[-–]\s*(.+?)(?:\n|$)")
    for match in issue_pattern.finditer(output):
        location = match.group(2)
        if match.group(3):
            location += f":{match.group(3)}"
        issues.append({
            "location": location,
            "description": match.group(4).strip(),
        })

    if verdict != "clean" and not issues:
        lines = output.split("\n")
        in_issues = False
        for line in lines:
            if "ISSUES:" in line.upper():
                in_issues = True
                continue
            if in_issues and line.strip().startswith(("-", "*", "•")):
                issues.append({
                    "location": "unknown",
                    "description": line.strip().lstrip("-*• "),
                })
            elif in_issues and re.match(r"\d+\.", line.strip()):
                issues.append({
                    "location": "unknown",
                    "description": re.sub(r"^\d+\.\s*", "", line.strip()),
                })
            elif in_issues and line.strip() == "":
                continue
            elif in_issues and any(kw in line.upper() for kw in ["SCORE:", "SUMMARY:", "VERDICT:", "SUGGESTIONS:"]):
                in_issues = False

    # Parse suggestions
    suggestions = []
    lines = output.split("\n")
    in_suggestions = False
    for line in lines:
        if "SUGGESTIONS:" in line.upper():
            in_suggestions = True
            continue
        if in_suggestions and any(kw in line.upper() for kw in ["SCORE:", "SUMMARY:", "VERDICT:", "ISSUES:", "THOUGHTS:"]):
            in_suggestions = False
            continue
        if in_suggestions and line.strip() == "":
            continue
        if in_suggestions and line.strip().lower() in ("none", "n/a", "-"):
            continue
        if in_suggestions:
            text = re.sub(r"^\d+\.\s*", "", line.strip()).lstrip("-*• ")
            if text:
                suggestions.append(text)

    return {
        "verdict": verdict,
        "score": score,
        "issues": issues,
        "suggestions": suggestions,
        "summary": summary,
        "thoughts": thoughts,
        "raw": output,
    }


def run_codex_review(config: CodeshockConfig, diff: str, trigger: str = "save") -> Optional[ReviewRecord]:
    if not diff.strip():
        return None

    files = get_changed_files(diff)
    if not files:
        return None

    # Check budget before calling
    allowed, reason = token_budget.can_call()
    if not allowed:
        return ReviewRecord(
            timestamp=time.time(), files=files, verdict="unknown", score=0,
            issues=[], suggestions=[], summary=f"Skipped: {reason}", thoughts="", trigger=trigger, diff_size=len(diff),
        )

    depth = config.review.depth
    if trigger == "push":
        depth = "thorough"
    elif trigger == "save" and depth == "thorough":
        depth = "standard"

    prompt_template = get_prompt_template(depth)
    prompt = prompt_template.format(
        files=", ".join(files),
        diff=diff[:15000],
    )

    # Lock to prevent concurrent API calls (causes 400 errors)
    with _codex_lock:
        try:
            result = subprocess.run(
                ["codex", "exec", prompt],
                capture_output=True,
                text=True,
                cwd=config.project_dir,
                timeout=120,
            )
            token_budget.record_call()
            output = result.stdout.strip()
            if not output:
                output = result.stderr.strip()
        except FileNotFoundError:
            output = "VERDICT: unknown\nSCORE: 0/10\nSUMMARY: codex CLI not found. Install with: npm i -g @openai/codex"
        except subprocess.TimeoutExpired:
            output = "VERDICT: unknown\nSCORE: 0/10\nSUMMARY: Review timed out after 120s"
        except Exception as e:
            output = f"VERDICT: unknown\nSCORE: 0/10\nSUMMARY: Review failed: {str(e)}"

    parsed = parse_review_output(output)

    return ReviewRecord(
        timestamp=time.time(),
        files=files,
        verdict=parsed["verdict"],
        score=parsed["score"],
        issues=parsed["issues"],
        suggestions=parsed.get("suggestions", []),
        summary=parsed["summary"],
        thoughts=parsed.get("thoughts", ""),
        trigger=trigger,
        diff_size=len(diff),
    )


def run_focus_review(config: CodeshockConfig, diff: str, focus: str) -> Optional[ReviewRecord]:
    if not diff.strip():
        return None

    files = get_changed_files(diff)
    prompt = f"""Focus your review on: {focus}. Be conversational — share your real thoughts.

Changed files: {", ".join(files)}

```diff
{diff[:15000]}
```

VERDICT: [clean|minor|issues|critical]
THOUGHTS: 2-3 sentences about {focus} specifically.
ISSUES: (numbered, file:line - description)
SUGGESTIONS: (numbered, specific improvements for {focus})
SCORE: X/10
SUMMARY: one line about {focus} specifically
"""

    allowed, reason = token_budget.can_call()
    if not allowed:
        return ReviewRecord(
            timestamp=time.time(), files=files, verdict="unknown", score=0,
            issues=[], suggestions=[], summary=f"Skipped: {reason}", thoughts="", trigger=f"focus:{focus}", diff_size=len(diff),
        )

    with _codex_lock:
        try:
            result = subprocess.run(
                ["codex", "exec", prompt],
                capture_output=True, text=True,
                cwd=config.project_dir, timeout=120,
            )
            token_budget.record_call()
            output = result.stdout.strip() or result.stderr.strip()
        except Exception as e:
            output = f"VERDICT: unknown\nSCORE: 0/10\nSUMMARY: Focus review failed: {str(e)}"

    parsed = parse_review_output(output)

    return ReviewRecord(
        timestamp=time.time(),
        files=files,
        verdict=parsed["verdict"],
        score=parsed["score"],
        issues=parsed["issues"],
        suggestions=parsed.get("suggestions", []),
        summary=parsed["summary"],
        thoughts=parsed.get("thoughts", ""),
        trigger=f"focus:{focus}",
        diff_size=len(diff),
    )


# --- Token budget tracking ---

class TokenBudget:
    """Track codex CLI calls to prevent runaway costs."""

    def __init__(self, max_calls_per_hour: int = 20, max_calls_per_session: int = 100):
        self.max_per_hour = max_calls_per_hour
        self.max_per_session = max_calls_per_session
        self._calls: list = []  # timestamps
        self._session_calls = 0

    def can_call(self) -> tuple:
        """Returns (allowed: bool, reason: str)."""
        now = time.time()
        # Clean old entries
        self._calls = [t for t in self._calls if now - t < 3600]

        if self._session_calls >= self.max_per_session:
            return False, f"Session limit reached ({self.max_per_session} calls). Restart codeshock to reset."

        if len(self._calls) >= self.max_per_hour:
            return False, f"Hourly limit reached ({self.max_per_hour}/hr). Wait a bit."

        return True, "ok"

    def record_call(self):
        self._calls.append(time.time())
        self._session_calls += 1

    @property
    def usage(self) -> dict:
        now = time.time()
        hourly = len([t for t in self._calls if now - t < 3600])
        return {
            "hourly": hourly,
            "hourly_limit": self.max_per_hour,
            "session": self._session_calls,
            "session_limit": self.max_per_session,
            "hourly_pct": round(hourly / self.max_per_hour * 100),
            "session_pct": round(self._session_calls / self.max_per_session * 100),
        }


# Global budget instance
token_budget = TokenBudget()


def run_codex_chat(project_dir: str, message: str) -> str:
    """Send a chat message to codex and get a response. Keep it short."""
    allowed, reason = token_budget.can_call()
    if not allowed:
        return f"Budget limit: {reason}"

    prompt = f"""You are a helpful code assistant. Be concise and conversational — 2-4 sentences max. No fluff.

The user is asking about their project. Answer directly.

User: {message}
"""
    with _codex_lock:
        try:
            result = subprocess.run(
                ["codex", "exec", prompt],
                capture_output=True,
                text=True,
                cwd=project_dir,
                timeout=60,
            )
            token_budget.record_call()
            output = result.stdout.strip()
            if not output:
                output = result.stderr.strip() or "No response from codex."
            return output
        except FileNotFoundError:
            return "codex CLI not found. Install with: npm i -g @openai/codex"
        except subprocess.TimeoutExpired:
            return "Timed out waiting for codex response."
        except Exception as e:
            return f"Error: {str(e)}"


CONVERSATION_REVIEW_PROMPT = """You are an independent senior engineer watching a live coding session. A developer is using an AI assistant (Claude Code) to write code. You have zero loyalty to either side. Your job is to be brutally honest.

Here's what just happened:

{conversation}

Think like a real human reviewing this. Not a polite AI. A real person who's seen a lot of code and has strong opinions.

Rules:
- If the AI gave bad advice or wrote questionable code, call it out. Don't be nice just because it's an AI.
- If the developer asked a bad question or is going down the wrong path, say so.
- If something could be done way better, explain what and why.
- If it's genuinely good, say that too. Don't nitpick for the sake of it.
- Rate honestly. A 5 is average. Most code is average. Don't hand out 8s and 9s unless it's actually impressive.
- Think about: correctness, security, performance, readability, maintainability, edge cases.

Respond in this format:
VERDICT: [clean|minor|issues|critical]
THOUGHTS: 3-5 sentences. Your unfiltered, honest reaction. What would you actually say to this developer if you were sitting next to them? Be specific, reference actual code or decisions you saw.
SUGGESTIONS:
1. The single best thing they could do differently right now (be specific and actionable)
2. Another suggestion if you have one (or skip if nothing else stands out)
SCORE: X/10
SUMMARY: one line, honest
"""


def run_conversation_review(project_dir: str, conversation_text: str) -> Optional[Dict]:
    """Review a Claude Code conversation exchange. Returns parsed review dict or None."""
    if not conversation_text.strip() or len(conversation_text.strip()) < 50:
        return None

    allowed, reason = token_budget.can_call()
    if not allowed:
        return None

    prompt = CONVERSATION_REVIEW_PROMPT.format(
        conversation=conversation_text[:8000],
    )

    with _codex_lock:
        try:
            result = subprocess.run(
                ["codex", "exec", prompt],
                capture_output=True,
                text=True,
                cwd=project_dir,
                timeout=120,
            )
            token_budget.record_call()
            output = result.stdout.strip()
            if not output:
                output = result.stderr.strip()
            if not output:
                return None
        except Exception:
            return None

    parsed = parse_review_output(output)
    return parsed
