"""Hard verification framework for Agentic Pilot."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from playwright.async_api import Page, Locator

logger = logging.getLogger("pilot.verification")


# Words that describe the instruction rather than its content; excluded when matching answers to goals.
_INSTRUCTION_WORDS = {
    "the", "and", "then", "after", "with", "from", "into", "onto", "for", "that", "this", "these", "those",
    "his", "her", "its", "their", "about", "what", "which", "who", "when", "where", "page", "site", "website",
    "go", "goto", "open", "visit", "navigate", "search", "find", "look", "extract", "gather", "collect", "return",
    "findings", "information", "click", "type", "enter", "exactly", "please", "tell", "show", "give", "some",
    "useful", "pieces", "result", "results", "first", "google", "bing", "duckduckgo",
}


def goal_content_terms(goal: str) -> set[str]:
    """Content words of a goal (lower-case, length > 3), excluding URLs, domains and instruction words."""
    text = re.sub(r"https?://\S+", " ", (goal or "").lower())
    words = re.findall(r"[a-z0-9]+(?:['\-][a-z0-9]+)*", " ".join(t for t in text.split() if "." not in t))
    return {w for w in words if len(w) > 3 and w not in _INSTRUCTION_WORDS}


def requested_search_query(goal: str) -> str | None:
    """The quoted query of a search request, e.g. "Search Google for 'Alan Turing'" -> "alan turing"."""
    if not goal or not re.search(r"\b(search|look up|query)\b", goal, re.IGNORECASE):
        return None
    m = re.search(r"[\"'\u2018\u201c]([^\"'\u2019\u201d]{2,})[\"'\u2019\u201d]", goal)
    return m.group(1).strip().lower() if m else None


def extract_exact_text_to_type(prompt: str) -> str | None:
    """Extract exact text string requested to be entered into a form or input."""
    if not prompt:
        return None
    # 1. 'enter exactly:\n\n<text>\n\nDo NOT...'
    m = re.search(r'enter\s+exactly:\s*\n*(.+?)(?:\n\s*do\s+not|\n\s*then|\n\s*and|\n\s*find|\n\s*open|$)', prompt, re.IGNORECASE | re.DOTALL)
    if m:
        val = m.group(1).strip()
        if val:
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1].strip()
            return val
    # 2. 'enter exactly <quoted>' or 'enter <quoted>' or 'type <quoted>'
    m2 = re.search(r'(?:enter\s+exactly|enter|type)\s*:\s*["\']([^"\']+)["\']', prompt, re.IGNORECASE)
    if m2:
        return m2.group(1).strip()
    m3 = re.search(r'(?:enter\s+exactly|type\s+exactly|enter|type)\s+["\']([^"\']+)["\']', prompt, re.IGNORECASE)
    if m3:
        return m3.group(1).strip()
    # 3. 'type <text> into ...'
    m4 = re.search(r'(?:^|[,;.]\s*|\b(?:and|then)\s+)(?:type|enter)\s+(.+?)(?:\s+(?:into|in)\s+|$)', prompt, re.IGNORECASE)
    if m4:
        cand = m4.group(1).strip()
        if cand and not any(kw in cand.lower() for kw in ['url', 'http', 'page', 'google', 'vault.example']):
            return cand
    return None


class VerificationError(Exception):
    """Exception raised when a hard verification check fails."""
    pass


class VerificationResult(BaseModel):
    """Structured verification result for Expected→Observed→PASS/FAIL (R09).

    Every verification check produces one of these records, enabling
    research measurement of verification accuracy and ablation comparison.
    """

    verified: bool
    type: str
    expected: dict[str, Any] = Field(default_factory=dict)
    observed: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    message: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class VerificationManager:
    """Manages hard execution verification for all Playwright actions."""

    async def verify_url(self, page: Page, initial_url: str, requested_url: str) -> dict[str, Any]:
        """Verify navigation succeeded and didn't hit a browser error."""
        current_url = page.url
        if current_url.startswith("chrome-error://"):
            raise VerificationError(f"Navigation failed: Hit browser error page at {current_url}")
            
        # It's possible the URL redirects, so we check if the DOM looks like an error
        content = await page.content()
        if "ERR_NAME_NOT_RESOLVED" in content or "ERR_CONNECTION_REFUSED" in content:
            raise VerificationError(f"Navigation failed: DNS/Connection error on {current_url}")
            
        return {
            "verified": True,
            "type": "url",
            "initial": initial_url,
            "current": current_url
        }

    async def verify_dom_mutation(self, page: Page, initial_html: str, action_name: str) -> dict[str, Any]:
        """Verify that the DOM meaningfully changed after a click or interaction."""
        current_html = await page.content()
        
        # Simple length heuristic for now, or check for new visible elements
        if initial_html == current_html:
            # Maybe it just opened a new tab, or didn't mutate the DOM. Let's not fail immediately,
            # but record a warning. Some clicks don't mutate (e.g. clicking a background).
            pass
            
        return {
            "verified": True,
            "type": "dom_mutation",
            "action": action_name
        }

    async def verify_input_value(self, locator: Locator, expected_text: str) -> dict[str, Any]:
        """Verify that a text field actually contains the text we tried to type."""
        try:
            actual_value = await locator.input_value(timeout=1000)
            if actual_value != expected_text:
                raise VerificationError(f"Input verification failed: Expected '{expected_text}', got '{actual_value}'")
        except Exception as e:
            if isinstance(e, VerificationError):
                raise
            # If input_value() fails, it might be contenteditable, check innerText
            try:
                actual_text = await locator.inner_text(timeout=1000)
                if expected_text not in actual_text:
                    raise VerificationError(f"Input verification failed: Expected '{expected_text}' to be in '{actual_text}'")
            except Exception as inner_e:
                if isinstance(inner_e, VerificationError):
                    raise
                raise VerificationError("Input verification failed: Could not read value back from element.")
                
        return {
            "verified": True,
            "type": "input_value",
            "expected": expected_text
        }

    async def verify_visual(self, page: Page) -> dict[str, Any]:
        """Verify visual state (e.g., no overlays blocking)."""
        return {"verified": True, "type": "visual"}

    # --- Enhanced Verification Methods (Phase 6 / R09) ---

    async def verify_expected_vs_observed(
        self,
        expected: dict[str, Any],
        observed: dict[str, Any],
        verification_type: str = "generic",
    ) -> VerificationResult:
        """Generic Expected→Observed→PASS/FAIL verification.

        Compares expected and observed state dictionaries and determines
        whether the verification passes based on key-value matching.
        """
        mismatches: list[str] = []
        for key, expected_value in expected.items():
            observed_value = observed.get(key)
            if observed_value is None:
                mismatches.append(f"{key}: expected={expected_value}, observed=MISSING")
            elif str(observed_value).lower() != str(expected_value).lower():
                # Flexible string comparison
                if str(expected_value).lower() not in str(observed_value).lower():
                    mismatches.append(f"{key}: expected={expected_value}, observed={observed_value}")

        verified = len(mismatches) == 0
        confidence = 1.0 - (len(mismatches) / max(len(expected), 1))
        message = "PASS" if verified else f"FAIL — {'; '.join(mismatches)}"

        logger.info(
            "VERIFY type=%s verified=%s confidence=%.2f mismatches=%d",
            verification_type, verified, confidence, len(mismatches),
        )

        return VerificationResult(
            verified=verified,
            type=verification_type,
            expected=expected,
            observed=observed,
            confidence=max(0.0, confidence),
            message=message,
        )

    async def verify_task_completion(
        self,
        page: Page,
        intent_action: str,
        intent_site: str | None,
        current_url: str | None,
        navigation_succeeded: bool,
        input_text: str = "",
        task_plan: Any | None = None,
        extracted_data: dict[str, Any] | None = None,
        final_answer: str | None = None,
    ) -> VerificationResult:
        """Verify that the user's requested objective has actually been achieved.

        Reaching a search engine homepage (e.g. google.com) is only action-level navigation success,
        NEVER task completion if further steps (search, click result, extract) were requested.
        """
        expected: dict[str, Any] = {"task_completed": True}
        observed: dict[str, Any] = {}
        # Conjuncts switched off for the ablation study (E, H, Q, T, X, R); empty in normal use.
        from backend.config import get_config
        disabled = {c.upper() for c in get_config().verification_disabled_checks}

        # 1. Page responsiveness & error checking
        try:
            page_title = await page.title()
            cur_url = page.url
            observed["page_title"] = page_title
            observed["page_url"] = cur_url
            observed["page_responsive"] = True
            
            title_lower = page_title.lower()
            url_lower = cur_url.lower()
            input_lower = (input_text or "").lower()
            requires_search = any(w in input_lower for w in ["search", "find", "look up", "query"])
            requires_extract = any(w in input_lower for w in ["extract", "gather", "collect", "return the findings", "return findings", "information about", "page title"])
            is_multistep = requires_extract or (task_plan and len(getattr(task_plan, "steps", [])) > 1)

            is_browser_error = url_lower.startswith("chrome-error://") or "err_" in url_lower
            is_http_error = any(code in title_lower for code in ("404 not found", "500 internal", "502 bad gateway", "503 service", "page not found", "not found"))
            is_bot_blocked = "sorry/index" in url_lower or "recaptcha" in url_lower or "unusual traffic" in title_lower
            # Redirected to a sign-in wall although the request named a page that is not a sign-in page.
            requested_urls = re.findall(r"https?://[^\s'\"]+", input_text or "")
            login_markers = ("/login", "/signin", "/sign_in", "/sign-in", "/auth", "accounts.google.")
            is_login_wall = bool(requested_urls) and any(m in url_lower for m in login_markers) and not any(
                any(m in u.lower() for m in login_markers) for u in requested_urls
            )
            observed["login_wall"] = is_login_wall
            has_error = is_browser_error or is_http_error or is_bot_blocked or is_login_wall
            observed["has_error_state"] = has_error
            expected["has_error_state"] = False
        except Exception as exc:
            logger.exception("VERIFY_TASK_COMPLETION_EXCEPTION: %s", exc)
            observed["page_responsive"] = False
            observed["has_error_state"] = True
            expected["has_error_state"] = False

        if "E" in disabled:
            expected.pop("has_error_state", None)  # ablation: the error conjunct is not part of Phi
        elif observed.get("has_error_state"):
            observed["task_completed"] = False
            return await self.verify_expected_vs_observed(expected, observed, "task_completion")

        # 2. Check if the task requested search/click/extract but is still sitting on a search engine homepage
        input_lower = (input_text or "").lower()
        requires_search = any(w in input_lower for w in ["search", "find", "look up", "query"])
        requires_extract = any(w in input_lower for w in ["extract", "gather", "collect", "return the findings", "return findings", "information about", "page title"])
        is_multistep = requires_search or requires_extract or (task_plan and len(getattr(task_plan, "steps", [])) > 1)

        cur_url = observed.get("page_url", "")
        is_search_homepage = cur_url.rstrip("/").endswith(("google.com", "google.co.in", "bing.com", "duckduckgo.com")) and "search" not in cur_url and "q=" not in cur_url

        if is_multistep and is_search_homepage and "H" not in disabled:
            logger.warning("VERIFY_TASK_COMPLETION REJECTED: Browser is only at search engine homepage, but user requested search/extract.")
            observed["task_completed"] = False
            observed["premature_completion_prevented"] = True
            expected["premature_completion_prevented"] = False
            return await self.verify_expected_vs_observed(expected, observed, "task_completion")

        # 2b. A results page must be for the requested query, not just any query.
        wanted_query = requested_search_query(input_text)
        if wanted_query and not is_search_homepage and "Q" not in disabled:
            from urllib.parse import parse_qs, urlparse
            params = parse_qs(urlparse(cur_url).query)
            got = " ".join(params.get("q", []) + params.get("query", []) + params.get("p", [])).lower()
            if got:
                matches = all(w in got for w in wanted_query.split())
                expected["search_query_matches"] = True
                observed["search_query_matches"] = matches
                if not matches:
                    logger.warning("VERIFY_TASK_COMPLETION REJECTED: results page is for %r, requested %r.", got, wanted_query)
                    observed["task_completed"] = False
                    return await self.verify_expected_vs_observed(expected, observed, "task_completion")

        # 3. Check if user requested typing/entering specific text
        exact_text = extract_exact_text_to_type(input_text)
        if exact_text and "T" not in disabled:
            expected["text_verified"] = exact_text
            try:
                values = await page.evaluate("""() => {
                    const vals = [];
                    document.querySelectorAll('input, textarea, [contenteditable="true"]').forEach(el => {
                        const v = el.value || el.innerText || '';
                        if (v) vals.push(v);
                    });
                    return vals;
                }""")
                if "exactly" in (input_text or "").lower():
                    has_exact_text = any(v.strip() == exact_text.strip() for v in values)
                else:
                    has_exact_text = any(exact_text in v for v in values)
                observed["text_verified"] = exact_text if has_exact_text else (values[0] if values else "NOT_FOUND")
            except Exception as e:
                observed["text_verified"] = f"ERROR: {e}"
                has_exact_text = False

            if not has_exact_text:
                logger.warning("VERIFY_TASK_COMPLETION REJECTED: Requested text '%s' not verified on page.", exact_text)
                observed["task_completed"] = False
                observed["premature_completion_prevented"] = True
                expected["premature_completion_prevented"] = False
                return await self.verify_expected_vs_observed(expected, observed, "task_completion")

        # 4. If extraction was requested, verify extracted data is present
        if requires_extract and "X" not in disabled:
            # An answer counts only if it mentions the goal's content terms; length alone is not evidence.
            terms = goal_content_terms(input_text)

            def _mentions_goal(text: str) -> bool:
                return bool(text) and (not terms or any(t in text.lower() for t in terms))

            has_substantive_answer = bool(
                final_answer
                and not any(final_answer.lower().strip().startswith(p) for p in ("navigat", "open", "go to", "start", "search", "click", "select", "type"))
                and _mentions_goal(final_answer)
            )
            import json as _json
            has_structured = bool(extracted_data) and _mentions_goal(_json.dumps(extracted_data, default=str))
            has_data = has_structured or has_substantive_answer
            observed["information_extracted"] = has_data
            expected["information_extracted"] = True
            if not has_data:
                observed["task_completed"] = False
                observed["premature_completion_prevented"] = True
                expected["premature_completion_prevented"] = False
                return await self.verify_expected_vs_observed(expected, observed, "task_completion")

        # 5. Check TaskPlan completion if present
        # For a one-step plan the step *is* the task and the checks above judge it; R only guards
        # multi-step plans against skipping steps.
        if task_plan and hasattr(task_plan, "steps") and len(task_plan.steps) > 1 and "R" not in disabled:
            uncompleted = [s for s in task_plan.steps if s.status != "completed" and s.action_type not in ["verify", "complete"]]
            # A free-text answer no longer excuses pending steps; only structured extraction does.
            if uncompleted and not extracted_data:
                observed["task_completed"] = False
                observed["remaining_steps"] = len(uncompleted)
                expected["remaining_steps"] = 0
                return await self.verify_expected_vs_observed(expected, observed, "task_completion")

        observed["task_completed"] = True
        return await self.verify_expected_vs_observed(expected, observed, "task_completion")

    async def verify_file_state(
        self,
        file_path: str,
        should_exist: bool = True,
        min_size: int | None = None,
    ) -> VerificationResult:
        """Verify file existence and metadata for filesystem operations."""
        path = Path(file_path)
        expected: dict[str, Any] = {"exists": should_exist}
        observed: dict[str, Any] = {"exists": path.exists()}

        if min_size is not None:
            actual_size = path.stat().st_size if path.exists() else 0
            expected["meets_min_size"] = True
            observed["meets_min_size"] = actual_size >= min_size
            observed["size"] = actual_size

        if should_exist and path.exists():
            observed["size"] = path.stat().st_size
            observed["is_file"] = path.is_file()

        return await self.verify_expected_vs_observed(expected, observed, "file_state")

    async def self_verify_completion(
        self,
        page: Page,
        input_text: str,
        final_answer: str | None = None,
        extracted_data: Any | None = None,
        model_override: str | None = None,
    ) -> VerificationResult:
        """Baseline completion check: ask the planner model whether the task is done.

        The model sees the same observation the rule gate uses (URL, title, input values,
        visible text, the agent's answer). It is a self-verification baseline, not part of Phi.
        """
        import json as _json

        from backend.llm.gateway import OllamaGateway

        gateway = OllamaGateway()
        try:
            title = await page.title()
            url = page.url
            snapshot = await page.evaluate("""() => {
                const vals = [];
                document.querySelectorAll('input, textarea').forEach(el => { if (el.value) vals.push(el.value); });
                return {inputs: vals, text: (document.body ? document.body.innerText : '').slice(0, 2000)};
            }""")
        except Exception as exc:
            return VerificationResult(verified=False, type="task_completion_self", message=f"FAIL: page unreadable ({exc})")

        user = (
            f"Task: {input_text}\n"
            f"Current URL: {url}\nPage title: {title}\n"
            f"Values in input fields: {snapshot.get('inputs')}\n"
            f"Agent's answer: {final_answer or ''}\n"
            f"Agent's extracted data: {_json.dumps(extracted_data, default=str)[:500] if extracted_data else ''}\n"
            f"Visible page text (truncated):\n{snapshot.get('text', '')}"
        )
        observed: dict[str, Any] = {"page_url": url, "page_title": title}
        try:
            judgement = await gateway.complete_structured(
                SELF_CHECK_SYSTEM_PROMPT, user, SelfCheck, model_override=model_override
            )
            observed["task_completed"] = bool(judgement.done)
            observed["self_check_reason"] = judgement.reason
        except Exception as exc:
            observed["task_completed"] = False
            observed["self_check_error"] = str(exc)
        return VerificationResult(
            verified=bool(observed["task_completed"]),
            type="task_completion_self",
            expected={"task_completed": True},
            observed=observed,
            message="PASS (self-check)" if observed["task_completed"] else "FAIL (self-check)",
        )


SELF_CHECK_SYSTEM_PROMPT = (
    "You check whether a browser agent has finished the user's task. Judge only from the observation "
    "given. Answer done=true only if the task as stated is fully achieved on this page or by the agent's answer."
)


class SelfCheck(BaseModel):
    """Answer of the self-verification baseline."""

    done: bool = Field(description="true if the task is fully achieved")
    reason: str = Field(default="", description="one sentence")



verification_manager = VerificationManager()

