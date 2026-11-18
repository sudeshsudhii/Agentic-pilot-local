"""Regression tests for page-content extraction.

`summarize_page_extraction` turns one page's title and extracted text snippet
into a findings list and a final answer. A prior implementation ignored both
inputs and returned a hardcoded "3 Useful Pieces of Information about
Kattankulathur Campus" template regardless of which page was visited -- a
leftover from one test fixture that had been generalised into production code.
Every extraction must be derived from the actual page content.
"""

from __future__ import annotations

from backend.agent.nodes import summarize_page_extraction


def test_reflects_the_actual_page_title_and_content():
    """The bug: the answer must name the real page, never a hardcoded campus."""
    answer, findings = summarize_page_extraction(
        "httpbin.org",
        "This domain is for use in illustrative examples in documents. "
        "You may use this domain in literature without prior coordination.",
    )
    assert "Kattankulathur" not in answer
    assert "SRM" not in answer
    assert answer.startswith("httpbin.org")
    assert len(findings) == 1
    assert "illustrative examples" in findings[0]


def test_uses_the_real_page_title_not_a_hardcoded_default():
    """The bug's sibling: the title fallback was a specific institution's name."""
    answer, _ = summarize_page_extraction("", "Some short page body text here that is long enough.")
    assert "SRM" not in answer
    assert answer.startswith("Untitled page")


def test_drops_navigation_boilerplate_lines():
    answer, findings = summarize_page_extraction(
        "Example Article",
        "Skip to main content\n"
        "Jump to navigation\n"
        "This is the actual substantive first paragraph of the article, long enough to count.\n"
        "Accept all cookies to continue browsing this website.\n",
    )
    assert len(findings) == 1
    assert "substantive first paragraph" in findings[0]
    assert all("skip to" not in f.lower() and "cookies" not in f.lower() for f in findings)


def test_falls_back_to_a_trimmed_snippet_when_nothing_survives_filtering():
    answer, findings = summarize_page_extraction("Short Page", "Hi\nok\n#tag\nhttp://x")
    assert findings == []
    assert "Short Page" in answer


def test_reports_no_content_when_the_snippet_is_empty():
    answer, findings = summarize_page_extraction("Empty Page", "")
    assert findings == []
    assert "No readable text content" in answer
