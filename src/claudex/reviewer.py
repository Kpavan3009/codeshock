import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import ClaudexConfig
from .session import ReviewRecord


REVIEW_PROMPT_TEMPLATE = """Review this code diff. The project context is in AGENTS.md.

Changed files: {files}

```diff
{diff}
```

Respond EXACTLY in this format:
VERDICT: [clean|minor|issues|critical]
ISSUES:
1. file:line - description
SCORE: X/10
SUMMARY: one line
"""

THOROUGH_PROMPT_TEMPLATE = """Do a thorough security and logic review of this diff. Check for:
- SQL injection, XSS, CSRF, command injection
- Authentication/authorization gaps
- Race conditions, null pointer issues
- Logic errors, off-by-one, boundary conditions
- Missing input validation
- Hardcoded secrets or credentials

The project context is in AGENTS.md.

Changed files: {files}

```diff
{diff}
```

Respond EXACTLY in this format:
VERDICT: [clean|minor|issues|critical]
ISSUES:
1. file:line - description
SCORE: X/10
SUMMARY: one line
"""

QUICK_PROMPT_TEMPLATE = """Quick scan of this diff for obvious bugs or security issues.

Changed files: {files}

```diff
{diff}
```

VERDICT: [clean|minor|issues|critical]
ISSUES: (numbered list or "none")
SCORE: X/10
SUMMARY: one line
"""

LEARN_PROMPT_TEMPLATE = """Review this code diff and explain your reasoning. The developer is learning.
For each issue found, explain WHY it's a problem and HOW to fix it.

Changed files: {files}

```diff
{diff}
```

VERDICT: [clean|minor|issues|critical]
ISSUES:
1. file:line - description
   WHY: explanation
   FIX: suggestion
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

    verdict_match = re.search(r"VERDICT:\s*(clean|minor|issues|critical)", output, re.IGNORECASE)
    if verdict_match:
        verdict = verdict_match.group(1).lower()

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
            elif in_issues and any(kw in line.upper() for kw in ["SCORE:", "SUMMARY:", "VERDICT:"]):
                in_issues = False

    return {
        "verdict": verdict,
        "score": score,
        "issues": issues,
        "summary": summary,
        "raw": output,
    }


def run_codex_review(config: ClaudexConfig, diff: str, trigger: str = "save") -> Optional[ReviewRecord]:
    if not diff.strip():
        return None

    files = get_changed_files(diff)
    if not files:
        return None

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

    try:
        result = subprocess.run(
            ["codex", "exec", prompt],
            capture_output=True,
            text=True,
            cwd=config.project_dir,
            timeout=120,
        )
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
        summary=parsed["summary"],
        trigger=trigger,
        diff_size=len(diff),
    )


def run_focus_review(config: ClaudexConfig, diff: str, focus: str) -> Optional[ReviewRecord]:
    if not diff.strip():
        return None

    files = get_changed_files(diff)
    prompt = f"""Focus your review specifically on: {focus}

Changed files: {", ".join(files)}

```diff
{diff[:15000]}
```

VERDICT: [clean|minor|issues|critical]
ISSUES: (numbered, file:line - description)
SCORE: X/10
SUMMARY: one line about {focus} specifically
"""

    try:
        result = subprocess.run(
            ["codex", "exec", prompt],
            capture_output=True, text=True,
            cwd=config.project_dir, timeout=120,
        )
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
        summary=parsed["summary"],
        trigger=f"focus:{focus}",
        diff_size=len(diff),
    )
