import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ReviewRecord:
    timestamp: float
    files: List[str]
    verdict: str
    score: int
    issues: List[Dict]
    summary: str
    trigger: str
    diff_size: int

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "ReviewRecord":
        return cls(**data)


class SessionManager:
    def __init__(self, claudex_dir: str):
        self.claudex_dir = Path(claudex_dir)
        self.session_file = self.claudex_dir / "session.jsonl"
        self.reviews_dir = self.claudex_dir / "reviews"
        self.reviews_dir.mkdir(exist_ok=True)
        self._reviews: List[ReviewRecord] = []
        self._start_time = time.time()
        self._load_session()

    def _load_session(self):
        if self.session_file.exists():
            try:
                for line in self.session_file.read_text().strip().split("\n"):
                    if line.strip():
                        data = json.loads(line)
                        if data.get("type") == "review":
                            self._reviews.append(ReviewRecord.from_dict(data["data"]))
            except Exception:
                pass

    def add_review(self, review: ReviewRecord):
        self._reviews.append(review)

        with open(self.session_file, "a") as f:
            entry = {"type": "review", "data": review.to_dict()}
            f.write(json.dumps(entry) + "\n")

        review_file = self.reviews_dir / f"{int(review.timestamp)}.json"
        review_file.write_text(json.dumps(review.to_dict(), indent=2))

    @property
    def reviews(self) -> List[ReviewRecord]:
        return self._reviews

    @property
    def session_duration(self) -> float:
        return time.time() - self._start_time

    @property
    def total_reviews(self) -> int:
        return len(self._reviews)

    @property
    def total_issues(self) -> int:
        return sum(len(r.issues) for r in self._reviews)

    @property
    def avg_score(self) -> float:
        if not self._reviews:
            return 0.0
        return sum(r.score for r in self._reviews) / len(self._reviews)

    @property
    def score_history(self) -> List[int]:
        return [r.score for r in self._reviews]

    def hot_files(self, limit: int = 5) -> List[tuple]:
        counts: Dict[str, int] = {}
        for r in self._reviews:
            for f in r.files:
                counts[f] = counts.get(f, 0) + 1
        sorted_files = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_files[:limit]

    def recurring_issues(self, limit: int = 5) -> List[tuple]:
        issue_texts: Dict[str, int] = {}
        for r in self._reviews:
            for issue in r.issues:
                desc = issue.get("description", "").strip().lower()
                words = desc.split()[:6]
                key = " ".join(words)
                if key:
                    issue_texts[key] = issue_texts.get(key, 0) + 1
        sorted_issues = sorted(issue_texts.items(), key=lambda x: x[1], reverse=True)
        return [(k, v) for k, v in sorted_issues if v >= 2][:limit]

    def generate_session_summary(self) -> str:
        if not self._reviews:
            return "No reviews in this session."

        lines = [
            f"Session duration: {self.session_duration / 60:.0f} minutes",
            f"Reviews: {self.total_reviews}",
            f"Avg score: {self.avg_score:.1f}/10",
            f"Issues found: {self.total_issues}",
            "",
        ]

        hot = self.hot_files(3)
        if hot:
            lines.append("Most reviewed files:")
            for f, count in hot:
                lines.append(f"  - {f} ({count} reviews)")
            lines.append("")

        recurring = self.recurring_issues(3)
        if recurring:
            lines.append("Recurring issues:")
            for desc, count in recurring:
                lines.append(f"  - {desc} ({count}x)")

        return "\n".join(lines)

    def save_session_summary(self):
        summary = self.generate_session_summary()
        summary_file = self.claudex_dir / "session-summary.md"
        summary_file.write_text(summary)

    def export_markdown(self) -> str:
        lines = [
            f"# Code Review Report",
            f"Session duration: {self.session_duration / 60:.0f} minutes | "
            f"Reviews: {self.total_reviews} | Avg score: {self.avg_score:.1f}/10",
            "",
        ]

        critical = [r for r in self._reviews if r.verdict == "critical"]
        if critical:
            lines.append("## Critical Issues")
            for r in critical:
                for issue in r.issues:
                    lines.append(f"- {issue.get('location', '?')} — {issue.get('description', '')}")
            lines.append("")

        issues = [r for r in self._reviews if r.verdict == "issues"]
        if issues:
            lines.append("## Issues Found")
            for r in issues:
                for issue in r.issues:
                    lines.append(f"- {issue.get('location', '?')} — {issue.get('description', '')}")
            lines.append("")

        recurring = self.recurring_issues()
        if recurring:
            lines.append("## Recurring Patterns")
            for desc, count in recurring:
                lines.append(f"- {desc} (appeared {count} times)")
            lines.append("")

        return "\n".join(lines)
