"""Regression tests for the completion-gate, CAPTCHA and routing fixes.

Each test corresponds to a false completion or false rejection found by the fixture study in
artifacts/experiments/verification_gate_study.py (case ids in the test names).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.browser.dom import detect_captcha
from backend.llm.analyzer import capability_analyzer
from backend.llm.parser import TaskPlan, TaskStep
from backend.llm.registry import ModelRegistry
from backend.llm.router import ModelRouter
from backend.verification.manager import (
    VerificationManager,
    extract_exact_text_to_type,
    goal_content_terms,
    requested_search_query,
)


def fake_page(url: str, title: str, input_values: list[str] | None = None) -> MagicMock:
    page = MagicMock()
    page.url = url
    page.title = AsyncMock(return_value=title)
    page.evaluate = AsyncMock(return_value=input_values or [])
    return page


async def decide(page, goal, **kw):
    res = await VerificationManager().verify_task_completion(
        page=page, intent_action="x", intent_site=None, current_url=page.url,
        navigation_succeeded=True, input_text=goal, **kw,
    )
    return res.verified


# --- helpers ---------------------------------------------------------------------------------

def test_goal_terms_drop_instruction_words_and_domains():
    terms = goal_content_terms("Go to wikipedia.org, search for 'Alan Turing' and extract his birth year")
    assert terms == {"alan", "turing", "birth", "year"}


def test_requested_query_is_the_quoted_text():
    assert requested_search_query("Search Google for 'Alan Turing'") == "alan turing"
    assert requested_search_query("Go to example.com") is None


@pytest.mark.parametrize("prompt", [
    "Search Google for the blood type of Alan Turing",   # "type of ..." is not a typing request
    "Search for Enter Sandman lyrics",                    # "Enter" is part of the query
])
def test_exact_text_pattern_does_not_hijack_ordinary_requests(prompt):
    assert extract_exact_text_to_type(prompt) is None


def test_exact_text_pattern_still_finds_typing_requests():
    assert extract_exact_text_to_type("Go to https://notes.example.com and enter exactly: 'Meeting at 10am'") == "Meeting at 10am"
    assert extract_exact_text_to_type("Open google.com and type cats into the search box") == "cats"


# --- completion predicate -------------------------------------------------------------------

@pytest.mark.asyncio
async def test_S7_results_for_another_query_are_rejected():
    goal = "Search Google for 'Alan Turing'"
    assert not await decide(fake_page("https://www.google.com/search?q=Grace+Hopper", "Grace Hopper - Search"), goal)
    assert await decide(fake_page("https://www.google.com/search?q=Alan+Turing", "Alan Turing - Search"), goal)


@pytest.mark.asyncio
async def test_N6_soft_404_title_is_rejected():
    assert not await decide(fake_page("https://example.com/pricing", "Page not found | Example"), "Go to https://example.com/pricing")


@pytest.mark.asyncio
async def test_N7_login_wall_redirect_is_rejected():
    page = fake_page("https://github.com/login?return_to=%2Fexplore", "Sign in to GitHub")
    assert not await decide(page, "Go to https://github.com/explore")
    # A requested login page is not a wall.
    page = fake_page("https://github.com/login", "Sign in to GitHub")
    assert await decide(page, "Go to https://github.com/login")


@pytest.mark.asyncio
async def test_T4_exact_request_needs_exact_value():
    goal = "Go to https://notes.example.com and enter exactly: 'Meeting at 10am'"
    assert not await decide(fake_page("https://notes.example.com/", "Notes", ["Meeting at 10am tomorrow"]), goal)
    assert await decide(fake_page("https://notes.example.com/", "Notes", ["Meeting at 10am"]), goal)


@pytest.mark.asyncio
async def test_X4_long_answer_without_goal_terms_is_rejected():
    goal = "Go to wikipedia.org, search for 'Alan Turing' and extract his birth year"
    page = fake_page("https://en.wikipedia.org/wiki/Alan_Turing", "Alan Turing - Wikipedia")
    vague = "The article describes an English mathematician and computer scientist regarded as a founder of the field."
    assert not await decide(page, goal, final_answer=vague, extracted_data={})
    generic = "The requested step has been carried out on the current page as the user instructed."
    assert not await decide(page, goal, final_answer=generic, extracted_data={})
    good = "Alan Turing was born on 23 June 1912 in Maida Vale, London."
    assert await decide(page, goal, final_answer=good, extracted_data={})


@pytest.mark.asyncio
async def test_P1_pending_step_not_excused_by_free_text_answer():
    plan = TaskPlan(task_summary="t", total_steps=2, steps=[
        TaskStep(step_index=1, description="open", action_type="navigate", status="completed"),
        TaskStep(step_index=2, description="click explore", action_type="click", status="pending"),
    ])
    page = fake_page("https://github.com/", "GitHub")
    assert not await decide(page, "Go to github.com, then open the Explore page",
                            task_plan=plan, final_answer="Explore page opened successfully as requested.")


# --- CAPTCHA detection ----------------------------------------------------------------------

def captcha_page(title: str, body: str, frames: list[tuple[str, bool]] | None = None) -> MagicMock:
    """Mock page; `frames` = [(src, visible)] returned for every challenge selector."""
    page = MagicMock()
    page.url = "https://example.org/"
    page.title = AsyncMock(return_value=title)
    frames = frames or []

    def locator(selector):
        loc = MagicMock()
        if selector == "body":
            loc.inner_text = AsyncMock(return_value=body)
            return loc
        hits = frames if "iframe" in selector else []
        loc.count = AsyncMock(return_value=len(hits))

        def nth(i):
            el = MagicMock()
            el.get_attribute = AsyncMock(return_value=hits[i][0])
            el.is_visible = AsyncMock(return_value=hits[i][1])
            return el

        loc.nth = nth
        return loc

    page.locator = locator
    return page


@pytest.mark.asyncio
async def test_C5_article_titled_robot_is_not_a_captcha():
    blocked, _ = await detect_captcha(captcha_page("Robot - Wikipedia", "A robot is a machine."))
    assert not blocked


@pytest.mark.asyncio
async def test_C6_invisible_or_hidden_recaptcha_is_not_a_challenge():
    frames = [("https://www.google.com/recaptcha/api2/anchor?size=invisible", True)]
    assert not (await detect_captcha(captcha_page("Sign in", "Sign in", frames)))[0]
    frames = [("https://www.google.com/recaptcha/api2/anchor", False)]
    assert not (await detect_captcha(captcha_page("Sign in", "Sign in", frames)))[0]


@pytest.mark.asyncio
async def test_visible_recaptcha_and_challenge_titles_still_block():
    frames = [("https://www.google.com/recaptcha/api2/anchor", True)]
    assert (await detect_captcha(captcha_page("Checkout", "Pay now", frames)))[0]
    assert (await detect_captcha(captcha_page("Are you a robot?", "")))[0]


# --- routing --------------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["Find a guitar guide on youtube.com", "Open the screening schedule on imdb.com"])
def test_keywords_match_whole_words_only(text):
    reqs = capability_analyzer.analyze(task_text=text, task_type="intent_parsing", complexity="low")
    assert reqs.target_role.value != "vision"


def test_stickiness_does_not_carry_across_tasks():
    reg = ModelRegistry()
    reg.mark_installed(["qwen2.5:1.5b", "qwen2.5:7b", "qwen3.5:2b", "deepseek-r1:1.5b", "moondream:latest"])
    router = ModelRouter(registry=reg)
    first = router.route(task_type="intent_parsing", input_text="Open google.com", complexity="low")
    # A new task starts with no active model: it must get the planner's preferred model, not the
    # model left over from the previous task.
    plan = router.route(task_type="planning", input_text="Go to a.com, then b.com", complexity="high", active_model=None)
    assert first.selected_model == "deepseek-r1:1.5b"
    assert plan.selected_model == "qwen3.5:2b"


# --- verify node ----------------------------------------------------------------------------

def _node_state(plan: TaskPlan, action_type: str, final_answer: str | None = None) -> dict:
    from backend.llm.parser import ActionResult, ParsedIntent, PlannedAction
    return {
        "task_id": "t-fix", "input_text": "Go to github.com, then open the Explore page", "session_id": None,
        "parsed_intent": ParsedIntent(action="navigate", risk_level="low", reasoning="r"),
        "planned_action": PlannedAction(action_type=action_type, reasoning="Explore page opened successfully as requested."),
        "action_history": [ActionResult(success=True, action_type="click", page_state_after="ready", duration_ms=1)],
        "task_plan": plan, "current_step_index": len(plan.steps), "retry_count": 0, "llm_call_count": 3,
        "status": "running", "error": None, "approved": False, "extracted_data": {}, "final_answer": final_answer,
        "action_manifest": None, "navigation_succeeded": True, "current_url": "https://github.com/",
    }


def _two_step_plan() -> TaskPlan:
    return TaskPlan(task_summary="t", total_steps=2, steps=[
        TaskStep(step_index=1, description="open", action_type="navigate", status="completed"),
        TaskStep(step_index=2, description="click explore", action_type="click", status="pending"),
    ])


@pytest.mark.asyncio
async def test_complete_action_does_not_mark_pending_step_done():
    from backend.agent import nodes
    page = fake_page("https://github.com/", "GitHub")
    with patch.object(nodes, "_get_task_page", AsyncMock(return_value=page)), \
         patch("backend.browser.dom.detect_captcha", AsyncMock(return_value=(False, ""))), \
         patch.object(nodes.database, "add_event", AsyncMock()), \
         patch.object(nodes.evidence_manager, "save_verification", MagicMock()):
        out = await nodes.verify_node(_node_state(_two_step_plan(), "complete",
                                                  final_answer="Explore page opened successfully as requested."))
    assert out["status"] == "running"  # premature completion rejected, loop continues


@pytest.mark.asyncio
async def test_verification_flag_disables_the_gate():
    from backend.agent import nodes
    page = fake_page("https://github.com/", "GitHub")
    cfg = nodes.get_config()
    with patch.object(nodes, "_get_task_page", AsyncMock(return_value=page)), \
         patch("backend.browser.dom.detect_captcha", AsyncMock(return_value=(False, ""))), \
         patch.object(nodes.database, "add_event", AsyncMock()), \
         patch.object(nodes.evidence_manager, "save_verification", MagicMock()), \
         patch.object(nodes.evidence_manager, "save_screenshot", MagicMock()), \
         patch.object(nodes.PlaywrightExecutor, "get_screenshot_with_dimensions", AsyncMock(return_value=(b"", 1, 1))), \
         patch.object(cfg, "enable_verification", False):
        out = await nodes.verify_node(_node_state(_two_step_plan(), "complete"))
    assert out["status"] == "completed"
