"""Regression tests for navigation loop protection.

`is_repeat_navigation` decides whether a planned "navigate" action should be
skipped because the browser is already on the requested page. The original
host-only comparison treated every page on a site as identical, so a deep link
into an already-visited site (e.g. a second Wikipedia article) was silently
skipped and the task ran against the wrong page while reporting success.
"""

from __future__ import annotations

from backend.agent.nodes import is_repeat_navigation


def test_does_not_skip_a_deep_link_into_an_already_visited_site():
    """The bug: a second article on the same host must not be treated as a repeat."""
    assert (
        is_repeat_navigation(
            "https://en.wikipedia.org/wiki/Main_Page",
            "https://en.wikipedia.org/wiki/Computer-aided_design",
        )
        is False
    )


def test_skips_navigation_to_the_same_page():
    assert is_repeat_navigation(
        "https://en.wikipedia.org/wiki/Robotics",
        "https://en.wikipedia.org/wiki/Robotics",
    ) is True


def test_skips_navigation_to_a_root_target_url():
    assert is_repeat_navigation("https://example.com/", "https://example.com") is True


def test_normalises_www_prefix():
    assert is_repeat_navigation("https://www.example.com/", "https://example.com/") is True


def test_does_not_skip_a_different_path_on_the_same_host():
    assert is_repeat_navigation("https://example.com/a", "https://example.com/b") is False


def test_ignores_query_string_when_comparing_paths():
    assert is_repeat_navigation("https://example.com/a?x=1", "https://example.com/a") is True
