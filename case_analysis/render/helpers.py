"""Small formatting/lookup helpers shared by transform.py and template.py."""
import html as _html
import re
from datetime import datetime


def e(v):
    return _html.escape(str(v)) if v is not None else ""


def fmt_date(s):
    if not s or s in ("NA", "N/A"):
        return "N/A"
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(s)


def fmt_month_year(s):
    if not s or s in ("NA", "N/A"):
        return ""
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt.strftime("%b %Y")
    except Exception:
        return ""


def fmt_date_short(s):
    if not s or s in ("NA", "N/A"):
        return ""
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt.strftime("%b %d")
    except Exception:
        return ""


def extract_note_date(note_raw):
    m = re.search(r"\d{4}-\d{2}-\d{2}", note_raw or "")
    if m:
        try:
            return datetime.fromisoformat(m.group(0)).strftime("%b %d, %Y")
        except Exception:
            pass
    return ""


def tag_in(tags, *keywords):
    for t in (tags or []):
        for kw in keywords:
            if kw.lower() in t.lower():
                return True
    return False


def classification_display(key):
    return {
        "product_bug": ("Product bug", "b-red"),
        "engineering_assisted_resolution": ("Engineering assisted resolution", "b-amber"),
        "cloud_outage": ("Cloud outage", "b-red"),
        "cloud_performance_issue": ("Cloud performance issue", "b-amber"),
        "infra_issue": ("Infra issue", "b-amber"),
        "product_performance": ("Product performance", "b-amber"),
        "performance": ("Performance", "b-amber"),  # legacy value — kept for older saved outputs
        "config_issue": ("Config issue", "b-blue"),
        "connectivity": ("Connectivity", "b-blue"),
        "upgrade_failure": ("Upgrade failure", "b-red"),
        "migration_issue": ("Migration issue", "b-amber"),
        "integration_connector": ("Integration / connector", "b-purple"),
        "extension_issue": ("Extension issue", "b-purple"),
        "license": ("License", "b-purple"),
        "security_assessment": ("Security assessment", "b-purple"),
        "feature_request": ("Feature request", "b-purple"),
        "other": ("Other", "b-gray"),
    }.get(key or "other", (key or "other", "b-gray"))


def status_color(status):
    s = (status or "").lower()
    if "closed" in s or "resolved" in s:
        return "b-green"
    elif "escalat" in s:
        return "b-red"
    elif "waiting" in s or "pending" in s or "customer action" in s:
        return "b-amber"
    return "b-blue"


def health_parse(raw):
    h = (raw or "Healthy").lower()
    if "healthy" in h:
        return "Healthy", "#27500A", "b-green", "No at-risk signals"
    elif "needs attention" in h or "attention" in h:
        return "Needs Attention", "#633806", "b-amber", "Mild signals — monitor"
    elif "at risk" in h:
        return "At Risk", "#791F1F", "b-red", "Escalation signals present"
    elif "blocked" in h:
        return "Blocked", "#791F1F", "b-red", "Hard blocker — act immediately"
    label = raw.split("—")[0].strip() if "—" in (raw or "") else (raw or "Unknown")
    return label, "#1a1a18", "b-gray", "Assessed from signals"


def mood_color(mood):
    m = (mood or "").lower()
    if "cooperative" in m:
        return "b-green"
    elif "frustrated" in m:
        return "b-red"
    return "b-gray"


def fmt_ticket(ticket_type, t):
    parts = [f"{ticket_type}-{t.get('id','')}"]
    if t.get("status"):
        parts.append(t["status"])
    if t.get("createdDate"):
        parts.append(f"opened {fmt_date_short(t['createdDate'])}")
    return " · ".join(parts)


def action_owner_badge(owner):
    if owner == "CLOSED":
        return {"label": "CLOSED", "color": "b-green"}
    elif owner == "Customer":
        return {"label": "Pending Customer", "color": "b-amber"}
    elif owner == "UiPath":
        return {"label": "Pending UiPath", "color": "b-blue"}
    return None
