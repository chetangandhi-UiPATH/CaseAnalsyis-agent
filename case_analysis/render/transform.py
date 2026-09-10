"""to_card_json — transforms the flat agent-output JSON into a card-aligned
JSON: display values (badges, labels, computed sub-text) are pre-computed
here so downstream consumers only ever read plain fields, never re-derive them.
"""
from .helpers import (
    action_owner_badge,
    classification_display,
    extract_note_date,
    fmt_date,
    fmt_date_short,
    fmt_month_year,
    fmt_ticket,
    health_parse,
    mood_color,
    status_color,
    tag_in,
)


def to_card_json(a: dict) -> dict:
    tags = a.get("tags") or []
    internal = a.get("internalDiscussion") or {}
    sme_involved = bool(internal.get("smeInvolved"))
    is_escalated = bool(a.get("isEscalated"))

    # ── header ────────────────────────────────────────────────────────────────
    cls_label, cls_color = classification_display(a.get("classification"))
    header = {
        "subject": a.get("subject", "N/A"),
        "accountName": a.get("accountName", "N/A"),
        "accountId": a.get("accountId"),
        "caseNumber": a.get("caseNumber", "N/A"),
        "owner": a.get("owner", "N/A"),
        "createdDate": fmt_date(a.get("caseCreatedDate", "")),
        "badges": {
            "priority": {
                "label": (a.get("priority") or "Medium") + " priority",
                "color": "b-gray"
            },
            "classification": {
                "label": cls_label,
                "color": cls_color
            },
            "status": {
                "label": a.get("status", "N/A"),
                "color": status_color(a.get("status", ""))
            }
        }
    }

    # ── metrics (4 boxes) ─────────────────────────────────────────────────────
    health_label, health_color, health_badge_color, health_sub = health_parse(a.get("caseHealth", "Healthy"))

    created_short = fmt_date_short(a.get("caseCreatedDate", ""))
    status_lower = (a.get("status") or "").lower()
    age_sub = (created_short + " → closed") if "closed" in status_lower or "resolved" in status_lower else (created_short + " → now") if created_short else ""

    prod_raw = a.get("product") or "N/A"
    prod_short = prod_raw.replace("Automation Suite", "AS").replace("Orchestrator", "Orch")
    if len(prod_short) > 18:
        prod_short = prod_short[:18] + "…"

    dep_raw = a.get("deployment_context_note") or "N/A"
    dep_type = a.get("deployment") or ""
    dep_sub = dep_type if dep_type and dep_type != "Unknown" else (dep_raw[:36] + ("…" if len(dep_raw) > 36 else ""))

    metrics = [
        {
            "label": "Case age",
            "value": a.get("caseAge", "N/A"),
            "valueColor": None,
            "valueFontSize": None,
            "sub": age_sub
        },
        {
            "label": "Customer health",
            "value": health_label,
            "valueColor": health_color,
            "valueFontSize": None,
            "sub": health_sub
        },
        {
            "label": "Escalation",
            "value": "SME" if sme_involved else ("Yes" if is_escalated else "None"),
            "valueColor": None,
            "valueFontSize": None,
            "sub": "Special handling" if sme_involved else ("Escalated" if is_escalated else "No escalation")
        },
        {
            "label": "Product",
            "value": prod_short,
            "valueColor": None,
            "valueFontSize": "14px",
            "sub": dep_sub
        }
    ]

    # ── issue classification ──────────────────────────────────────────────────
    bug_ref = a.get("bugReference")
    if bug_ref and bug_ref.get("type") in ("jira", "documentation"):
        bug_ref_display = bug_ref.get("link") or "N/A"
    elif bug_ref and bug_ref.get("type") == "none":
        bug_ref_display = "No Jira or doc link found"
    else:
        bug_ref_display = None

    confirm_status = a.get("bugConfirmationStatus")
    confirm_badge = (
        {"label": "Customer confirmed fixed", "color": "b-green"} if confirm_status == "customer_confirmed_fixed" else
        ({"label": "Engineering assisted fix", "color": "b-amber"} if confirm_status == "engineering_assisted_fix" else None)
    )

    issue_classification = {
        "classificationBadge": {"label": cls_label, "color": cls_color},
        "origin": a.get("issueOrigin", "N/A"),
        "rootCause": a.get("rootCause", "N/A"),
        "bugReference": bug_ref_display,
        "bugConfirmationBadge": confirm_badge,
        "deploymentType": dep_type or "Unknown",
        "deploymentContext": dep_raw,
        "versionRisk": "Yes" if a.get("version_risk") else "No",
        "productGeneration": a.get("productGeneration") or "N/A",
        "tags": tags
    }

    # ── resolution timeline ───────────────────────────────────────────────────
    resolution_timeline = [
        {
            "step": s.get("step", i + 1),
            "description": s.get("description", ""),
            "date": s.get("date_range", s.get("date", ""))
        }
        for i, s in enumerate(a.get("resolution_timeline") or [])
    ]

    # ── support actions ───────────────────────────────────────────────────────
    tech = (a.get("technicalGuidance") or "N/A")
    tech_disp = tech[:350] + ("…" if len(tech) > 350 else "")
    next_act = (a.get("nextAction") or "N/A")
    next_disp = next_act[:200] + ("…" if len(next_act) > 200 else "")
    action_badge = action_owner_badge(a.get("actionOwner", "N/A"))

    init_delay_flag = a.get("initialResponseDelayFlag", "NA")
    init_delay_badge = (
        {"label": "Delayed", "color": "b-amber"} if init_delay_flag == "delayed" else
        ({"label": "On time", "color": "b-green"} if init_delay_flag == "on_time" else None)
    )

    comm_pattern = a.get("communicationPattern") or {}
    back_and_forth = a.get("backAndForthCount")
    comm_value = f"{back_and_forth} exchange{'s' if back_and_forth != 1 else ''}" if back_and_forth is not None else "N/A"
    comm_badge = {"label": "Excessive", "color": "b-amber"} if comm_pattern.get("assessment") == "excessive" else None

    log_pattern = a.get("logRequestPattern") or {}
    log_count = log_pattern.get("count", 0)
    log_value = log_pattern.get("note") or (f"{log_count} request{'s' if log_count != 1 else ''}" if log_count else "None")
    log_badge = {"label": "Repetitive", "color": "b-amber"} if log_pattern.get("assessment") == "repetitive" else None

    support_actions = {
        "left": [
            {"key": "Guidance",     "value": tech_disp,                              "badge": None},
            {"key": "Call",         "value": a.get("callStatus", "N/A"),              "badge": None},
            {"key": "Resolution",   "value": a.get("resolution_summary", "N/A"),      "badge": None},
            {"key": "Next action",  "value": a.get("actionOwner", "N/A"),             "badge": action_badge}
        ],
        "right": [
            {"key": "Delays — UiPath",    "value": a.get("delaysUipath", "None identified"),   "badge": None},
            {"key": "Delays — Customer",  "value": a.get("delaysCustomer", "None identified"),  "badge": None},
            {"key": "Initial response",   "value": a.get("initialResponseDelay", "N/A"),        "badge": init_delay_badge},
            {"key": "Back-and-forth",     "value": comm_value,                                   "badge": comm_badge},
            {"key": "Log requests",       "value": log_value,                                    "badge": log_badge},
            {"key": "Post-resolution",    "value": next_disp,                                    "badge": None}
        ]
    }

    # ── customer signals ──────────────────────────────────────────────────────
    # Derive the display from initial vs final directly rather than trusting
    # the model's `trajectory` label on its own — if the two ever disagree
    # (e.g. trajectory="stable" but initial != final), showing "stable" would
    # bury a real mood change instead of surfacing it precisely.
    trend = a.get("sentimentTrend") or {}
    initial_mood = trend.get("initial")
    final_mood = trend.get("final") or a.get("customerMood")
    trend_display = None
    if initial_mood and final_mood:
        if initial_mood == final_mood:
            trend_display = f"Stable — {initial_mood} throughout"
        else:
            arrow = "↑" if trend.get("trajectory") == "improved" else "↓" if trend.get("trajectory") == "declined" else "→"
            trend_display = f"{initial_mood} {arrow} {final_mood}"

    customer_signals = {
        "moodBadge": {
            "label": a.get("customerMood", "Neutral"),
            "color": mood_color(a.get("customerMood", ""))
        },
        "reason": a.get("customerMoodReason", ""),
        "trend": trend_display,
        "trendReason": trend.get("reason") if trend.get("reason") and trend["reason"] != "NA" else None,
        "escalationRisk": "Present" if is_escalated else "None",
        "businessImpact": a.get("businessImpact", "None stated"),
        "evidence": (a.get("sentiment_evidence") or [])[:3]
    }

    # ── product signals ───────────────────────────────────────────────────────
    pain_points = a.get("pain_points") or []
    psf = a.get("productSpecificFeedback") or []
    support_pain = a.get("supportPainPoints") or []

    # Split productSpecificFeedback by type
    edu_items = [f for f in psf if f.get("type") == "customer_education"]
    other_psf = [f for f in psf if f.get("type") != "customer_education"]

    if pain_points:
        pp = pain_points[0]
        component = pp.get("product") or pp.get("subComponent") or ""
        sub = pp.get("subComponent") or ""
        comp_label = f"{component} · {sub}" if sub and sub != component else component
        prod_section = {
            "sectionLabel": "PAIN POINT",
            "rows": [
                {"key": "Component",   "value": comp_label,               "badge": None},
                {"key": "Description", "value": pp.get("description", ""), "badge": None},
                {"key": "Severity",    "value": None,                      "badge": {"label": "Medium", "color": "b-amber"}}
            ]
        }
    elif edu_items:
        ei = edu_items[0]
        prod_section = {
            "sectionLabel": "CUSTOMER EDUCATION",
            "rows": [
                {"key": "Component",  "value": ei.get("product", ""),    "badge": None},
                {"key": "Gap",        "value": ei.get("detail", ""),      "badge": None},
                {"key": "Action",     "value": ei.get("workaround", ""),  "badge": None}
            ]
        }
    elif other_psf:
        pf = other_psf[0]
        prod_section = {
            "sectionLabel": "PRODUCT FEEDBACK",
            "rows": [
                {"key": "Component", "value": pf.get("product", ""), "badge": None},
                {"key": "Detail",    "value": pf.get("detail", ""),  "badge": None}
            ]
        }
    else:
        prod_section = {
            "sectionLabel": None,
            "rows": []
        }

    product_signals = {
        "section": prod_section,
        "gaps": [g.get("observation", "") for g in support_pain[:3]]
    }

    # ── escalation & internal ─────────────────────────────────────────────────
    esc_type_badge = (
        {"label": "SME involvement", "color": "b-purple"} if sme_involved else
        ({"label": "Customer escalation", "color": "b-red"} if is_escalated else None)
    )

    escalation_internal = {
        "escalated": "Yes — SME special handling" if sme_involved else ("Yes — escalated" if is_escalated else "No"),
        "escalationTypeBadge": esc_type_badge,
        "whoInvolved": "SME · EMEA escalation contacts assigned" if sme_involved else ("Case owner" if is_escalated else "—"),
        "internalNote": {
            "text": internal.get("summary", "No internal activity recorded"),
            "date": extract_note_date(internal.get("lastInternalNote", ""))
        }
    }

    # ── context flags (10 items, ordered as in HTML) ──────────────────────────
    context_flags = [
        {"label": "Cloud outage",      "active": bool(a.get("cloud_outage"))},
        {"label": "Cloud perf issue",  "active": tag_in(tags, "cloud_performance_issue")},
        {"label": "Active migration",  "active": tag_in(tags, "migration", "active_migration")},
        {"label": "Decommission",      "active": tag_in(tags, "decommission")},
        {"label": "Joint session",     "active": tag_in(tags, "joint_session", "joint_execution")},
        {"label": "Storage constraint","active": tag_in(tags, "storage")},
        {"label": "Post-upgrade",      "active": tag_in(tags, "post_upgrade", "upgrade")},
        {"label": "SRE dependency",    "active": bool(a.get("sre_dependency"))},
        {"label": "TIF dependency",    "active": bool(a.get("tif_dependency"))},
        {"label": "Version risk",      "active": bool(a.get("version_risk"))}
    ]

    # ── case health & recommended action ─────────────────────────────────────
    linked = a.get("linked_tickets") or []
    jira_sre = " | ".join(fmt_ticket(t.get("type", ""), t) for t in linked) if linked else "None linked"

    tif_ticket = a.get("tif_ticket")
    tif_display = fmt_ticket("TIF", tif_ticket) if tif_ticket else "No TIF referenced"

    case_health = {
        "healthBadge": {"label": health_label, "color": health_badge_color},
        "repeatIssue": "Not detected — no cross-case matches" if not a.get("recurringIssue") else "Yes — recurring issue detected",
        "jiraSre": jira_sre,
        "tif": tif_display,
        "recommendedAction": next_act
    }

    # ── footer ────────────────────────────────────────────────────────────────
    my = fmt_month_year(a.get("caseCreatedDate", ""))
    footer = {
        "left": f"Case {a.get('caseNumber','N/A')} · {a.get('accountName','N/A')} · Generated by Support Intelligence Engine",
        "right": f"Schema v1.0{' · ' + my if my else ''}"
    }

    return {
        "header": header,
        "metrics": metrics,
        "issueClassification": issue_classification,
        "resolutionTimeline": resolution_timeline,
        "supportActions": support_actions,
        "customerSignals": customer_signals,
        "productSignals": product_signals,
        "escalationInternal": escalation_internal,
        "contextFlags": context_flags,
        "caseHealth": case_health,
        "summary": a.get("caseSummary"),
        "footer": footer,
        "meta": {
            "caseId": a.get("caseId"),
            "caseNumber": a.get("caseNumber"),
            "accountId": a.get("accountId"),
            "jobId": a.get("jobId"),
            "schemaVersion": "1.0"
        }
    }
