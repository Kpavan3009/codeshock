import time
import threading
from typing import List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

from .session import SessionManager, ReviewRecord


VERDICT_STYLES = {
    "clean": ("bold green", "CLEAN"),
    "minor": ("bold yellow", "MINOR"),
    "issues": ("bold red", "ISSUES"),
    "critical": ("bold white on red", "CRITICAL"),
    "unknown": ("bold dim", "?????"),
}

VERDICT_ICONS = {
    "clean": "●",
    "minor": "▲",
    "issues": "▲▲",
    "critical": "◆◆",
    "unknown": "?",
}

TRIGGER_LABELS = {
    "save": "save",
    "commit": "commit",
    "push": "push",
}


def format_time_ago(ts: float) -> str:
    delta = time.time() - ts
    if delta < 60:
        return f"{int(delta)}s ago"
    elif delta < 3600:
        return f"{int(delta / 60)}m ago"
    else:
        return f"{int(delta / 3600)}h ago"


def sparkline(values: List[int], width: int = 8) -> str:
    if not values:
        return ""
    blocks = " ▁▂▃▄▅▆▇█"
    if len(values) > width:
        values = values[-width:]
    min_v = min(values) if values else 0
    max_v = max(values) if values else 10
    span = max_v - min_v if max_v != min_v else 1
    return "".join(blocks[min(8, int((v - min_v) / span * 8))] for v in values)


def build_review_card(review: ReviewRecord) -> Panel:
    style, label = VERDICT_STYLES.get(review.verdict, VERDICT_STYLES["unknown"])
    icon = VERDICT_ICONS.get(review.verdict, "?")
    trigger = TRIGGER_LABELS.get(review.trigger, review.trigger)

    header = Text()
    header.append(f" {icon} ", style=style)
    header.append(f"{label}", style=style)
    header.append(f"  {format_time_ago(review.timestamp)}", style="dim")
    header.append(f"  [{trigger}]", style="dim italic")

    content = Text()
    content.append("\n")

    files_display = ", ".join(f[:20] for f in review.files[:3])
    if len(review.files) > 3:
        files_display += f" +{len(review.files) - 3}"
    content.append(f"  Files: {files_display}\n", style="dim")

    if review.issues:
        content.append("\n")
        for i, issue in enumerate(review.issues[:4], 1):
            loc = issue.get("location", "?")
            desc = issue.get("description", "")[:50]
            content.append(f"  {i}. ", style="dim")
            content.append(f"{loc}", style="bold cyan")
            content.append(f"\n     {desc}\n", style="white")
        if len(review.issues) > 4:
            content.append(f"\n  +{len(review.issues) - 4} more issues\n", style="dim")
    elif review.summary:
        content.append(f"\n  {review.summary}\n", style="dim")

    content.append(f"\n  Score: ", style="dim")
    score_style = "bold green" if review.score >= 8 else "bold yellow" if review.score >= 5 else "bold red"
    content.append(f"{review.score}/10", style=score_style)
    content.append("\n")

    border_style = "green" if review.verdict == "clean" else "yellow" if review.verdict == "minor" else "red" if review.verdict in ("issues", "critical") else "dim"

    return Panel(
        Text.assemble(header, content),
        border_style=border_style,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def build_stats_panel(session: SessionManager) -> Panel:
    duration = session.session_duration
    mins = int(duration / 60)
    hrs = int(mins / 60)
    if hrs > 0:
        time_str = f"{hrs}h {mins % 60}m"
    else:
        time_str = f"{mins}m"

    content = Text()
    content.append(f"  Session: {time_str}\n", style="dim")
    content.append(f"  Reviews: {session.total_reviews}\n", style="dim")
    content.append(f"  Issues:  {session.total_issues}\n", style="dim")

    avg = session.avg_score
    score_style = "bold green" if avg >= 8 else "bold yellow" if avg >= 5 else "bold red"
    if avg > 0:
        content.append(f"  Avg:     ", style="dim")
        content.append(f"{avg:.1f}/10\n", style=score_style)

    scores = session.score_history
    if scores:
        spark = sparkline(scores)
        trend = "↑" if len(scores) > 1 and scores[-1] >= scores[0] else "↓" if len(scores) > 1 else "–"
        content.append(f"\n  Trend: {spark} {trend}\n", style="dim")

    return Panel(
        content,
        title="[bold]Stats[/bold]",
        border_style="blue",
        box=box.ROUNDED,
        padding=(0, 0),
    )


def build_hotfiles_panel(session: SessionManager) -> Panel:
    hot = session.hot_files(5)
    content = Text()
    if not hot:
        content.append("  No data yet\n", style="dim")
    else:
        max_count = hot[0][1] if hot else 1
        for fname, count in hot:
            bar_len = max(1, int(count / max_count * 5))
            bar = "█" * bar_len + "░" * (5 - bar_len)
            short_name = fname if len(fname) <= 16 else "..." + fname[-13:]
            content.append(f"  {short_name:16s} {bar} {count}\n", style="dim")

    return Panel(
        content,
        title="[bold]Hot Files[/bold]",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(0, 0),
    )


def build_recurring_panel(session: SessionManager) -> Panel:
    recurring = session.recurring_issues(4)
    content = Text()
    if not recurring:
        content.append("  None yet\n", style="dim")
    else:
        for i, (desc, count) in enumerate(recurring, 1):
            content.append(f"  {i}. {desc[:30]}", style="yellow")
            content.append(f" ({count}x)\n", style="dim")

    return Panel(
        content,
        title="[bold]Recurring[/bold]",
        border_style="yellow",
        box=box.ROUNDED,
        padding=(0, 0),
    )


def build_dashboard(session: SessionManager, max_reviews: int = 6) -> Layout:
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )

    header = Panel(
        Align.center(Text("claudex", style="bold white")),
        style="blue",
        box=box.HEAVY,
    )
    layout["header"].update(header)

    layout["body"].split_column(
        Layout(name="stats_row", size=8),
        Layout(name="reviews", ratio=1),
    )

    layout["stats_row"].split_row(
        Layout(name="stats"),
        Layout(name="hotfiles"),
        Layout(name="recurring"),
    )

    layout["stats_row"]["stats"].update(build_stats_panel(session))
    layout["stats_row"]["hotfiles"].update(build_hotfiles_panel(session))
    layout["stats_row"]["recurring"].update(build_recurring_panel(session))

    reviews = session.reviews[-max_reviews:]
    if reviews:
        review_panels = []
        for review in reversed(reviews):
            review_panels.append(build_review_card(review))
        from rich.console import Group
        layout["reviews"].update(Panel(
            Group(*review_panels),
            title="[bold]Reviews[/bold]",
            border_style="dim",
            box=box.ROUNDED,
        ))
    else:
        layout["reviews"].update(Panel(
            Align.center(
                Text("\n\n  Watching for changes...\n\n  Make edits in Claude Code and reviews will appear here.\n\n", style="dim italic"),
            ),
            title="[bold]Reviews[/bold]",
            border_style="dim",
            box=box.ROUNDED,
        ))

    last_review = format_time_ago(reviews[-1].timestamp) if reviews else "never"
    footer_text = Text()
    footer_text.append(" claudex v1.0", style="bold blue")
    footer_text.append(" │ ", style="dim")
    footer_text.append("Watching", style="green")
    footer_text.append(" │ ", style="dim")
    footer_text.append(f"Last: {last_review}", style="dim")
    footer_text.append(" │ ", style="dim")
    footer_text.append("[d]etail [h]istory [f]ocus [p]ause [q]uit", style="dim italic")

    layout["footer"].update(Panel(footer_text, box=box.SIMPLE))

    return layout


class ReviewDashboard:
    def __init__(self, session: SessionManager):
        self.session = session
        self.console = Console()
        self._live: Optional[Live] = None
        self._running = False
        self._paused = False

    def start(self):
        self._running = True
        self._live = Live(
            build_dashboard(self.session),
            console=self.console,
            refresh_per_second=1,
            screen=True,
        )
        self._live.start()
        self._refresh_loop()

    def _refresh_loop(self):
        while self._running:
            try:
                if self._live and not self._paused:
                    self._live.update(build_dashboard(self.session))
                time.sleep(1)
            except Exception:
                pass

    def refresh(self):
        if self._live and not self._paused:
            try:
                self._live.update(build_dashboard(self.session))
            except Exception:
                pass

    def stop(self):
        self._running = False
        if self._live:
            try:
                self._live.stop()
            except Exception:
                pass

    def toggle_pause(self):
        self._paused = not self._paused
