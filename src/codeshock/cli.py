import sys
import signal
import threading
import click

from . import __version__
from .config import load_config, init_codeshock_dir
from .context import sync_context
from .session import SessionManager
from .watcher import CodeshockWatcher
from .display import ReviewDashboard
from .launcher import launch_tmux_session, attach_session, is_session_running, check_dependencies


@click.group(invoke_without_command=True)
@click.option("--project-dir", "-p", default=None, help="Project directory (default: current)")
@click.option("--mode", "-m", default="standard", type=click.Choice(["quick", "standard", "thorough", "paranoid", "learn"]))
@click.version_option(version=__version__)
@click.pass_context
def main(ctx, project_dir, mode):
    ctx.ensure_object(dict)
    ctx.obj["project_dir"] = project_dir
    ctx.obj["mode"] = mode

    if ctx.invoked_subcommand is None:
        start(project_dir, mode)


def start(project_dir, mode):
    config = load_config(project_dir)
    config.review.depth = mode

    codeshock_dir = init_codeshock_dir(project_dir)
    config.codeshock_dir = str(codeshock_dir)

    click.echo(f"codeshock v{__version__}")
    click.echo(f"Project: {config.project_dir}")
    click.echo(f"Mode: {mode}")
    click.echo("")

    click.echo("Syncing context (CLAUDE.md → AGENTS.md)...")
    sync_context(config)
    click.echo("Context synced.")
    click.echo("")

    deps = check_dependencies()
    if not deps["tmux"]:
        click.echo("tmux not found. Running in dashboard-only mode.")
        click.echo("Install tmux for the full split-terminal experience: brew install tmux")
        click.echo("")
        run_dashboard_standalone(config)
        return

    click.echo("Launching split terminal...")
    success = launch_tmux_session(config)
    if success:
        attach_session()
    else:
        click.echo("Failed to launch tmux session. Running standalone.")
        run_dashboard_standalone(config)


def run_dashboard_standalone(config):
    session = SessionManager(config.codeshock_dir)
    dashboard = ReviewDashboard(session)

    watcher = CodeshockWatcher(config, session, lambda review: dashboard.refresh())

    def shutdown(sig, frame):
        click.echo("\nShutting down...")
        watcher.stop()
        session.save_session_summary()
        dashboard.stop()
        sync_context(config)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    watcher.start()
    dashboard.start()


@main.command()
@click.option("--project-dir", "-p", default=None)
def dashboard(project_dir):
    config = load_config(project_dir)
    codeshock_dir = init_codeshock_dir(project_dir)
    config.codeshock_dir = str(codeshock_dir)

    session = SessionManager(config.codeshock_dir)
    dash = ReviewDashboard(session)

    watcher = CodeshockWatcher(config, session, lambda review: dash.refresh())

    def shutdown(sig, frame):
        watcher.stop()
        session.save_session_summary()
        dash.stop()
        sync_context(config)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    watcher.start()
    dash.start()


@main.command()
@click.option("--project-dir", "-p", default=None)
def sync(project_dir):
    config = load_config(project_dir)
    init_codeshock_dir(project_dir)
    config.codeshock_dir = str(init_codeshock_dir(project_dir))
    path = sync_context(config)
    click.echo(f"Context synced to {path}")
    click.echo(f"AGENTS.md written to {config.project_dir}/AGENTS.md")


@main.command()
@click.option("--project-dir", "-p", default=None)
def reviews(project_dir):
    config = load_config(project_dir)
    codeshock_dir = init_codeshock_dir(project_dir)
    session = SessionManager(str(codeshock_dir))

    if not session.reviews:
        click.echo("No reviews found.")
        return

    for review in session.reviews:
        verdict_display = {
            "clean": click.style("CLEAN", fg="green", bold=True),
            "minor": click.style("MINOR", fg="yellow", bold=True),
            "issues": click.style("ISSUES", fg="red", bold=True),
            "critical": click.style("CRITICAL", fg="red", bold=True, underline=True),
        }.get(review.verdict, review.verdict)

        import datetime
        ts = datetime.datetime.fromtimestamp(review.timestamp).strftime("%H:%M:%S")
        files = ", ".join(review.files[:3])

        click.echo(f"  {ts}  {verdict_display}  {review.score}/10  {files}")
        if review.issues:
            for issue in review.issues[:3]:
                click.echo(f"         {issue.get('location', '?')} - {issue.get('description', '')}")
        click.echo("")


@main.command()
@click.option("--project-dir", "-p", default=None)
def stats(project_dir):
    config = load_config(project_dir)
    codeshock_dir = init_codeshock_dir(project_dir)
    session = SessionManager(str(codeshock_dir))

    click.echo(f"Reviews: {session.total_reviews}")
    click.echo(f"Issues:  {session.total_issues}")
    click.echo(f"Avg:     {session.avg_score:.1f}/10")
    click.echo("")

    hot = session.hot_files()
    if hot:
        click.echo("Hot files:")
        for f, c in hot:
            click.echo(f"  {f} ({c} reviews)")
        click.echo("")

    recurring = session.recurring_issues()
    if recurring:
        click.echo("Recurring issues:")
        for desc, c in recurring:
            click.echo(f"  {desc} ({c}x)")


@main.command(name="export")
@click.option("--project-dir", "-p", default=None)
@click.option("--format", "-f", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
@click.option("--output", "-o", default=None)
def export_reviews(project_dir, fmt, output):
    config = load_config(project_dir)
    codeshock_dir = init_codeshock_dir(project_dir)
    session = SessionManager(str(codeshock_dir))

    if fmt == "markdown":
        content = session.export_markdown()
    else:
        import json
        content = json.dumps([r.to_dict() for r in session.reviews], indent=2)

    if output:
        with open(output, "w") as f:
            f.write(content)
        click.echo(f"Exported to {output}")
    else:
        click.echo(content)


@main.command()
@click.option("--project-dir", "-p", default=None)
def init(project_dir):
    codeshock_dir = init_codeshock_dir(project_dir)
    config = load_config(project_dir)
    config.codeshock_dir = str(codeshock_dir)
    sync_context(config)
    click.echo(f"Initialized .codeshock/ in {codeshock_dir.parent}")
    click.echo(f"Config: {codeshock_dir}/config.toml")
    click.echo(f"AGENTS.md written to {config.project_dir}/AGENTS.md")


if __name__ == "__main__":
    main()
