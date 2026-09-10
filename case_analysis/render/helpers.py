"""Small formatting/lookup helpers used by transform.py."""
import re
from datetime import datetime


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


# Exact classification values the prompt is instructed to emit.
_CLASSIFICATION_DISPLAY = {
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
    "by_design": ("By design", "b-gray"),
}

# If a classification value shows up that isn't an exact match above (a typo,
# a legacy run, a value the prompt hasn't been told about yet), infer the
# closest real category from keywords in the value itself rather than
# collapsing everything unmatched into one meaningless "Other" bucket.
_KEYWORD_FALLBACKS = [
    (("bug", "defect"), ("Product bug", "b-red")),
    (("assisted_resolution", "assisted resolution", "engineering_assist"), ("Engineering assisted resolution", "b-amber")),
    (("cloud_outage", "cloud outage"), ("Cloud outage", "b-red")),
    (("cloud_perf", "cloud performance"), ("Cloud performance issue", "b-amber")),
    (("infra",), ("Infra issue", "b-amber")),
    (("performance", "perf", "slow"), ("Product performance", "b-amber")),
    (("config",), ("Config issue", "b-blue")),
    (("connect",), ("Connectivity", "b-blue")),
    (("upgrade",), ("Upgrade failure", "b-red")),
    (("migrat",), ("Migration issue", "b-amber")),
    (("integration", "connector"), ("Integration / connector", "b-purple")),
    (("extension", "plugin"), ("Extension issue", "b-purple")),
    (("licens",), ("License", "b-purple")),
    (("security",), ("Security assessment", "b-purple")),
    (("feature", "enhancement"), ("Feature request", "b-purple")),
    (("design", "expected", "documented"), ("By design", "b-gray")),
]


def classification_display(key):
    if not key:
        return ("Uncategorized", "b-gray")

    exact = _CLASSIFICATION_DISPLAY.get(key)
    if exact:
        return exact

    lowered = key.lower()
    for keywords, display in _KEYWORD_FALLBACKS:
        if any(kw in lowered for kw in keywords):
            return display

    # No known keyword matched either — show the model's own value, cleaned
    # up for display, rather than a generic label that hides what it actually said.
    return (key.replace("_", " ").replace("-", " ").strip().capitalize(), "b-gray")


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
