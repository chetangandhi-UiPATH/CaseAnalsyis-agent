"""Facts computed straight from Salesforce data — never left to the LLM to estimate."""
import re
from datetime import date as _date
from datetime import datetime as _datetime
from typing import Optional

_INITIAL_RESPONSE_SLA_HOURS = 24

# Fixed UiPath product-generation lookup — Act-1 (classic RPA platform) vs Act-2
# (agentic/AI platform). This is a known mapping, not something the LLM should
# guess at, so it's applied here to whatever product name(s) the classifier put
# in the `product` field rather than asked of the LLM directly.
_ACT1_PRODUCTS = {
    "studio", "studiox", "studio web", "robot", "activities", "assistant",
    "document understanding", "du", "apps", "ai center", "process mining",
    "task mining", "acr",
}
_ACT2_PRODUCTS = {
    "agents", "maestro", "autopilot", "ixp", "ixp unstructured docs",
    "ai trust layer", "uipath cli", "test cloud", "test manager",
}


def product_generation(product_str: Optional[str]) -> Optional[str]:
    """Classify the product(s) named in the `product` field as "Act-1" (classic
    RPA platform) or "Act-2" (agentic/AI platform). When both appear on one
    case, Act-2 takes priority since it's the more specific signal. None if no
    named product matches either list (includes platform/infrastructure
    products like Orchestrator)."""
    if not product_str:
        return None
    names = [p.split(":")[0].strip().lower() for p in product_str.split("|") if p.strip()]
    if any(n in _ACT2_PRODUCTS for n in names):
        return "Act-2"
    if any(n in _ACT1_PRODUCTS for n in names):
        return "Act-1"
    return None


_NA_VALUES = {"", "na", "n/a"}


def _clean_sentence(text: Optional[str]) -> str:
    text = (text or "").strip()
    return "" if text.lower() in _NA_VALUES else text


def _first_sentence(text: Optional[str]) -> str:
    """issue_summary is allowed to run 2-3 sentences; a composed caseSummary
    only has room for one clause per source field, so take just the opener."""
    text = _clean_sentence(text)
    if not text:
        return ""
    idx = text.find(". ")
    return text[: idx + 1] if idx != -1 else text


def _clean_next_action(text: Optional[str]) -> str:
    """nextAction reads like '[Deployment] [Product] — [risk] -> [action].' —
    strip the routing prefix so it reads as a plain sentence in a summary."""
    text = _clean_sentence(text)
    if not text:
        return ""
    if "→" in text:
        text = text.split("→", 1)[1].strip()
    return text[:1].upper() + text[1:] if text else text


def compose_case_summary(merged: dict) -> str:
    """Deterministic caseSummary built from fields the two analysis calls
    already produced (issue_summary, resolution_summary, nextAction) instead
    of a third LLM call re-deriving the same content in different words. All
    three source fields already come from prompts under the same
    no-dates/no-tier-names/no-personal-names guardrails as everything else,
    so the composed result inherits that compliance for free."""
    issue = _first_sentence(merged.get("issue_summary"))
    next_action = _clean_next_action(merged.get("nextAction"))

    # The closed-case nextAction format ("Case resolved and closed. ... No
    # further action required.") already restates what was resolved — pairing
    # it with resolution_summary too would just say the same thing twice.
    if next_action.lower().startswith("case resolved and closed"):
        parts = [issue, next_action]
    else:
        parts = [issue, _clean_sentence(merged.get("resolution_summary")), next_action]

    parts = [p for p in parts if p]
    return " ".join(parts) if parts else "NA"


def build_linked_tickets(raw: dict) -> list[dict]:
    """Build linked_tickets deterministically from SF data — never rely on the LLM for this."""
    tickets = []
    seen_ids = set()

    def _add_jira(jira_raw, status=None):
        for jira_id in re.split(r"[\s,;|]+", jira_raw or ""):
            jira_id = jira_id.strip()
            if jira_id and jira_id not in seen_ids:
                tickets.append({"type": "Jira", "id": jira_id, "status": status})
                seen_ids.add(jira_id)

    # 1. Parent Jira_Key__c — may hold multiple keys comma/space separated
    _add_jira(raw.get("Jira_Key__c"))

    # 2. Child cases (inline Cases subquery) — ER/TIF/SRE stored as child cases.
    #    Each child may also carry its own Jira_Key__c.
    ticket_pat = re.compile(r"^(ER|TIF|SRE)\s*:\s*(\S+)", re.IGNORECASE)
    for child in (raw.get("Cases") or {}).get("records", []):
        subject = child.get("Subject") or ""
        status = child.get("Status") or None
        _add_jira(child.get("Jira_Key__c"), status)
        m = ticket_pat.match(subject.strip())
        if m:
            ticket_id = m.group(2)
            if ticket_id not in seen_ids:
                tickets.append({"type": m.group(1).upper(), "id": ticket_id, "status": status})
                seen_ids.add(ticket_id)

    return tickets


def compute_case_age(raw: dict) -> Optional[str]:
    created_date_str = (raw.get("CreatedDate") or "")[:10]  # "YYYY-MM-DD"
    closed_date_str = (raw.get("ClosedDate") or "")[:10]
    try:
        created_dt = _date.fromisoformat(created_date_str)
        end_dt = _date.fromisoformat(closed_date_str) if closed_date_str else _date.today()
        return f"{(end_dt - created_dt).days} days"
    except Exception:
        return None


def _parse_sf_datetime(value: Optional[str]) -> Optional[_datetime]:
    if not value:
        return None
    try:
        return _datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _format_duration(delta) -> str:
    total_hours = delta.total_seconds() / 3600
    if total_hours < 1:
        return "under 1 hour"
    days, hours = divmod(int(total_hours), 24)
    if days == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    if hours == 0:
        return f"{days} day{'s' if days != 1 else ''}"
    return f"{days} day{'s' if days != 1 else ''} {hours} hour{'s' if hours != 1 else ''}"


def compute_communication_metrics(raw: dict) -> dict:
    """Deterministic facts from email timestamps — initial-response delay and
    back-and-forth volume are objective counts, not left to the LLM to estimate."""
    emails = (raw.get("EmailMessages") or {}).get("records", [])
    timeline = sorted(
        ((dt, bool(e.get("Incoming"))) for e in emails if (dt := _parse_sf_datetime(e.get("MessageDate")))),
        key=lambda x: x[0],
    )

    metrics = {
        "emailExchangeCount": len(timeline),
        "backAndForthCount": sum(1 for i in range(1, len(timeline)) if timeline[i][1] != timeline[i - 1][1]),
        "initialResponseDelay": "NA",
        "initialResponseDelayFlag": "NA",
    }

    created_dt = _parse_sf_datetime(raw.get("CreatedDate"))
    first_outbound_dt = next((dt for dt, incoming in timeline if not incoming), None)
    if created_dt and first_outbound_dt:
        delta = first_outbound_dt - created_dt
        metrics["initialResponseDelay"] = _format_duration(delta)
        metrics["initialResponseDelayFlag"] = (
            "delayed" if delta.total_seconds() / 3600 > _INITIAL_RESPONSE_SLA_HOURS else "on_time"
        )

    return metrics
