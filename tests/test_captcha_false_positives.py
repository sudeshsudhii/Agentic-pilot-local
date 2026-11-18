"""Regression tests for CAPTCHA detection false positives.

`detect_captcha` must flag genuine bot-challenge pages (Google's /sorry/ page,
reCAPTCHA iframes, "I'm not a robot" interstitials) without flagging ordinary
articles that merely mention robots, bots, or CAPTCHAs as a topic. A prior
substring check (`"robot" in title`) flagged any page whose title contained
that five-letter word, including an encyclopedia article titled
"Robotics - Wikipedia".
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.browser.dom import detect_captcha


def _mock_page(url: str, title: str, body_text: str = "", selector_count: int = 0) -> AsyncMock:
    page = AsyncMock()
    page.url = url
    page.title.return_value = title
    body = AsyncMock()
    body.inner_text.return_value = body_text
    page.locator.return_value = body
    page.locator.return_value.count.return_value = selector_count
    return page


@pytest.mark.asyncio
async def test_does_not_flag_an_article_about_robotics():
    """The bug: a title merely containing 'robot' is not a bot challenge."""
    page = _mock_page(
        url="https://en.wikipedia.org/wiki/Robotics",
        title="Robotics - Wikipedia",
        body_text="Robotics is an interdisciplinary branch of engineering and science. " * 20,
    )
    is_captcha, _ = await detect_captcha(page)
    assert is_captcha is False


@pytest.mark.asyncio
async def test_does_not_flag_an_article_about_programming_language_named_in_url():
    page = _mock_page(
        url="https://en.wikipedia.org/wiki/Computer-aided_design",
        title="Computer-aided design - Wikipedia",
        body_text="Computer-aided design (CAD) is the use of computers to aid in design. " * 20,
    )
    is_captcha, _ = await detect_captcha(page)
    assert is_captcha is False


@pytest.mark.asyncio
async def test_still_flags_a_genuine_not_a_robot_interstitial():
    page = _mock_page(
        url="https://www.google.com/sorry/index?continue=x",
        title="Sorry...",
        body_text="Our systems have detected unusual traffic. Please verify you are human.",
    )
    is_captcha, _ = await detect_captcha(page)
    assert is_captcha is True


@pytest.mark.asyncio
async def test_still_flags_an_im_not_a_robot_title():
    page = _mock_page(url="https://example.com/challenge", title="I'm not a robot")
    is_captcha, _ = await detect_captcha(page)
    assert is_captcha is True


@pytest.mark.asyncio
async def test_does_not_flag_a_url_containing_the_word_captcha_as_an_article_topic():
    """The bug's sibling: bare 'captcha' in a URL path matched an article about CAPTCHAs."""
    page = _mock_page(
        url="https://en.wikipedia.org/wiki/CAPTCHA",
        title="CAPTCHA - Wikipedia",
        body_text="A CAPTCHA is a type of challenge-response test used in computing. " * 20,
    )
    is_captcha, _ = await detect_captcha(page)
    assert is_captcha is False


@pytest.mark.asyncio
async def test_still_flags_a_recaptcha_url():
    page = _mock_page(url="https://www.google.com/recaptcha/api2/anchor", title="reCAPTCHA")
    is_captcha, _ = await detect_captcha(page)
    assert is_captcha is True
