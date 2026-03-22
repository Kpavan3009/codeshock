from claudex.reviewer import parse_review_output, get_changed_files


def test_parse_clean_review():
    output = """VERDICT: clean
SCORE: 10/10
SUMMARY: No issues found"""
    result = parse_review_output(output)
    assert result["verdict"] == "clean"
    assert result["score"] == 10
    assert result["summary"] == "No issues found"
    assert result["issues"] == []


def test_parse_review_with_issues():
    output = """VERDICT: issues
ISSUES:
1. auth.js:42 - Missing input validation on user parameter
2. api.js:18 - No rate limiting on login endpoint
SCORE: 6/10
SUMMARY: Two security issues found"""
    result = parse_review_output(output)
    assert result["verdict"] == "issues"
    assert result["score"] == 6
    assert len(result["issues"]) == 2
    assert result["issues"][0]["location"] == "auth.js:42"
    assert "input validation" in result["issues"][0]["description"]


def test_parse_critical_review():
    output = """VERDICT: critical
ISSUES:
1. config.js:5 - Hardcoded database password in source code
SCORE: 2/10
SUMMARY: Credentials exposed in source"""
    result = parse_review_output(output)
    assert result["verdict"] == "critical"
    assert result["score"] == 2
    assert len(result["issues"]) == 1


def test_get_changed_files():
    diff = """diff --git a/auth.js b/auth.js
index 1234567..abcdefg 100644
--- a/auth.js
+++ b/auth.js
@@ -1,3 +1,4 @@
+const validate = require('./validate');
 function login(user, pass) {
diff --git a/api.js b/api.js
--- a/api.js
+++ b/api.js
"""
    files = get_changed_files(diff)
    assert "auth.js" in files
    assert "api.js" in files


def test_parse_unknown_format():
    output = "Something unexpected happened"
    result = parse_review_output(output)
    assert result["verdict"] == "unknown"
    assert result["score"] == 0
