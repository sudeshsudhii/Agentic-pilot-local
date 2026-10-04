"""Independent task oracle Phi* for the end-to-end runs.

The oracle decides whether a task was achieved from signals the agent and its verifier do not use:
server-side records of the local sites (cart, form submissions, notes, autosaved field values), the
final URL, and the ground-truth facts written into the site data. It calls no model and shares no
code with backend/verification. Unsatisfiable tasks are never achieved.
"""

from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlsplit


def _norm(s: str) -> str:
    return " ".join((s or "").split()).lower()


def _mentions(text: str, needle: str) -> bool:
    return re.search(r"(?<![\w])" + re.escape(needle.lower()) + r"(?![\w])", text.lower()) is not None


def evaluate(oracle: dict, final_url: str | None, answer_text: str, state: dict) -> tuple[bool, str]:
    """Return (achieved, reason) for one episode."""

    kind = oracle["type"]
    if kind == "unsatisfiable":
        return False, "task cannot be completed"

    if kind == "answer_contains":
        hit = next((v for v in oracle["any"] if _mentions(answer_text or "", v)), None)
        return hit is not None, f"answer {'contains ' + repr(hit) if hit else 'lacks the fact'}"

    if kind == "final_url":
        if not final_url:
            return False, "no final URL"
        u = urlsplit(final_url)
        ok = u.path.rstrip("/") == oracle["path"].rstrip("/")
        if ok and oracle.get("query_contains"):
            q = " ".join(v for vals in parse_qs(u.query).values() for v in vals)
            ok = _norm(oracle["query_contains"]) in _norm(q)
        return ok, f"final URL {final_url}"

    if kind == "cart":
        cart = state.get("cart", {})
        ok = all(cart.get(sku) == n for sku, n in oracle["items"].items()) and set(cart) == set(oracle["items"])
        return ok, f"cart {cart}"

    if kind == "contact":
        want = oracle["fields"]
        for sub in state.get("contact", []):
            if all(_norm(sub.get(k, "")) == _norm(v) for k, v in want.items()):
                return True, "matching submission"
        return False, f"{len(state.get('contact', []))} submissions, none matching"

    if kind == "newsletter":
        for sub in state.get("newsletter", []):
            if _norm(sub.get("email", "")) == _norm(oracle["email"]) and (
                "weekly" not in oracle or sub.get("weekly") == oracle["weekly"]
            ):
                return True, "subscribed"
        return False, "no matching subscription"

    if kind == "note":
        for n in state.get("notes", []):
            if _norm(n.get("title", "")) == _norm(oracle["title"]) and _norm(oracle["body_contains"]) in _norm(n.get("body", "")):
                return True, "note saved"
        return False, "no matching note"

    if kind == "draft":
        value = state.get("drafts", {}).get(oracle["page"], {}).get(oracle["field"])
        ok = value is not None and value.strip() == oracle["equals"]
        if ok and oracle.get("no_submission") and state.get(oracle["no_submission"]):
            return False, "form was submitted although the task said not to"
        if ok and oracle.get("not_path") and final_url and urlsplit(final_url).path.startswith(oracle["not_path"]):
            return False, "search was submitted although the task said not to"
        return ok, f"field value {value!r}"

    raise ValueError(f"unknown oracle type {kind}")


def answer_text_of(final_state: dict) -> str:
    """Collect everything the agent offered as its answer."""

    parts = []
    result = final_state.get("result") or {}
    for v in (result.get("answer"), final_state.get("final_answer"), result.get("extracted_data"), final_state.get("extracted_data")):
        if v:
            parts.append(v if isinstance(v, str) else json.dumps(v, default=str))
    return "\n".join(parts)
