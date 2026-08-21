"""Facts computed straight from Salesforce data — never left to the LLM to estimate."""
import re
from datetime import date as _date
from datetime import datetime as _datetime
from typing import Optional

_INITIAL_RESPONSE_SLA_HOURS = 24


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
