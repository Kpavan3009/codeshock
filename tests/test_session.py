import tempfile
import time
from pathlib import Path

from codeshock.session import SessionManager, ReviewRecord


def make_review(verdict="clean", score=8, files=None, issues=None):
    return ReviewRecord(
        timestamp=time.time(),
        files=files or ["test.js"],
        verdict=verdict,
        score=score,
        issues=issues or [],
        summary="Test review",
        trigger="save",
        diff_size=100,
    )


def test_session_add_review():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = SessionManager(tmpdir)
        review = make_review()
        session.add_review(review)
        assert session.total_reviews == 1
        assert session.avg_score == 8.0


def test_session_stats():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = SessionManager(tmpdir)
        session.add_review(make_review(score=8))
        session.add_review(make_review(score=6))
        session.add_review(make_review(score=10))
        assert session.total_reviews == 3
        assert session.avg_score == 8.0


def test_hot_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = SessionManager(tmpdir)
        session.add_review(make_review(files=["auth.js"]))
        session.add_review(make_review(files=["auth.js"]))
        session.add_review(make_review(files=["api.js"]))
        hot = session.hot_files()
        assert hot[0][0] == "auth.js"
        assert hot[0][1] == 2


def test_session_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        session1 = SessionManager(tmpdir)
        session1.add_review(make_review(score=7))
        session1.add_review(make_review(score=9))

        session2 = SessionManager(tmpdir)
        assert session2.total_reviews == 2


def test_export_markdown():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = SessionManager(tmpdir)
        session.add_review(make_review(
            verdict="critical",
            score=3,
            issues=[{"location": "auth.js:42", "description": "SQL injection"}],
        ))
        md = session.export_markdown()
        assert "Critical Issues" in md
        assert "SQL injection" in md


def test_score_history():
    with tempfile.TemporaryDirectory() as tmpdir:
        session = SessionManager(tmpdir)
        session.add_review(make_review(score=5))
        session.add_review(make_review(score=7))
        session.add_review(make_review(score=9))
        assert session.score_history == [5, 7, 9]
