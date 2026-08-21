"""render_card — pure template over the card dict produced by transform.to_card_json.
Zero display logic lives here; every value it prints was already decided upstream.
"""
from .helpers import e

_CSS = """
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f4f0;color:#1a1a18;padding:24px;font-size:14px}
  .page{max-width:900px;margin:0 auto;background:#fff;border-radius:12px;border:0.5px solid #d3d1c7;padding:24px}
  .header{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:14px;border-bottom:0.5px solid #d3d1c7;margin-bottom:16px}
  .case-title{font-size:16px;font-weight:600;color:#1a1a18;margin-bottom:5px}
  .case-meta{display:flex;gap:12px;flex-wrap:wrap}
  .meta-chip{font-size:12px;color:#5f5e5a;display:flex;align-items:center;gap:4px}
  .h-right{display:flex;gap:8px;align-items:center;flex-shrink:0;margin-left:16px}
  .badge{font-size:11px;padding:3px 10px;border-radius:10px;font-weight:500;white-space:nowrap}
  .b-green{background:#EAF3DE;color:#27500A}
  .b-amber{background:#FAEEDA;color:#633806}
  .b-red{background:#FCEBEB;color:#791F1F}
  .b-purple{background:#EEEDFE;color:#3C3489}
  .b-blue{background:#E6F1FB;color:#0C447C}
  .b-gray{background:#F1EFE8;color:#5f5e5a;border:0.5px solid #b4b2a9}
  .grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
  .grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:14px}
  .metric{background:#f5f4f0;border-radius:8px;padding:12px 14px}
  .metric-label{font-size:11px;color:#888780;margin-bottom:4px}
  .metric-val{font-size:20px;font-weight:600;color:#1a1a18;line-height:1}
  .metric-sub{font-size:11px;color:#888780;margin-top:3px}
  .card{background:#fff;border:0.5px solid #d3d1c7;border-radius:10px;padding:14px 16px;margin-bottom:12px}
  .card-title{font-size:11px;font-weight:600;color:#888780;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px}
  .kv{display:flex;gap:8px;margin-bottom:6px;align-items:flex-start}
  .kv-k{font-size:12px;color:#888780;min-width:124px;flex-shrink:0;padding-top:1px}
  .kv-v{font-size:12px;color:#1a1a18;line-height:1.5;flex:1}
  hr{border:none;border-top:0.5px solid #d3d1c7;margin:10px 0}
  .tag-row{display:flex;flex-wrap:wrap;gap:5px;margin-top:4px}
  .tag{font-size:11px;padding:2px 8px;border-radius:10px;border:0.5px solid #b4b2a9;color:#5f5e5a}
  .step{display:flex;gap:10px;align-items:flex-start;padding:6px 0;border-bottom:0.5px solid #e8e6e0}
  .step:last-child{border-bottom:none}
  .step-num{font-size:11px;font-weight:600;color:#888780;min-width:18px;padding-top:2px}
  .step-text{font-size:12px;color:#1a1a18;line-height:1.5;flex:1}
  .step-date{font-size:11px;color:#888780;white-space:nowrap;padding-top:2px}
  .signal-row{display:flex;gap:8px;align-items:flex-start;padding:5px 0;border-bottom:0.5px solid #e8e6e0}
  .signal-row:last-child{border-bottom:none}
  .signal-icon{font-size:13px;color:#888780;padding-top:1px;min-width:16px}
  .signal-text{font-size:12px;color:#5f5e5a;line-height:1.5;flex:1}
  .flag-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
  .flag{display:flex;align-items:center;gap:6px;font-size:12px;padding:6px 8px;border-radius:8px;background:#f5f4f0}
  .flag-true{color:#1a1a18}
  .flag-false{color:#888780}
  .dot-true{width:7px;height:7px;border-radius:50%;background:#639922;flex-shrink:0}
  .dot-false{width:7px;height:7px;border-radius:50%;background:#b4b2a9;flex-shrink:0}
  .internal-note{border-left:2px solid #AFA9EC;padding-left:10px;margin-top:8px}
  .internal-note-text{font-size:12px;color:#5f5e5a;line-height:1.5}
  .internal-note-meta{font-size:11px;color:#888780;margin-top:3px}
  .action-box{background:#f5f4f0;border-radius:8px;padding:10px 12px;margin-top:4px}
  .action-label{font-size:11px;color:#888780;margin-bottom:4px;font-weight:500}
  .action-text{font-size:12px;color:#1a1a18;line-height:1.5}
  .gap-row{display:flex;gap:8px;align-items:flex-start;padding:5px 0;border-bottom:0.5px solid #e8e6e0}
  .gap-row:last-child{border-bottom:none}
  .gap-icon{font-size:13px;color:#BA7517;padding-top:1px;min-width:16px}
  .gap-text{font-size:12px;color:#5f5e5a;line-height:1.5;flex:1}
  .footer{margin-top:16px;padding-top:12px;border-top:0.5px solid #d3d1c7;display:flex;justify-content:space-between;align-items:center}
  .footer-text{font-size:11px;color:#888780}
"""


def _b(badge):
    if not badge:
        return ""
    return f'<span class="badge {e(badge["color"])}">{e(badge["label"])}</span>'


def _kv(key, val_html):
    return f'<div class="kv"><span class="kv-k">{e(key)}</span><span class="kv-v">{val_html}</span></div>'


def _kv_row(row):
    if row.get("badge"):
        return _kv(row["key"], _b(row["badge"]))
    return _kv(row["key"], e(row.get("value") or ""))


def render_card(c: dict) -> str:
    h = c["header"]
    badges = h["badges"]

    # ── header ────────────────────────────────────────────────────────────────
    header_html = f"""
  <div class="header">
    <div>
      <div class="case-title">{e(h['subject'])}</div>
      <div class="case-meta">
        <span class="meta-chip">&#127970; {e(h['accountName'])}</span>
        <span class="meta-chip"># {e(h['caseNumber'])}</span>
        <span class="meta-chip">&#128100; {e(h['owner'])}</span>
        <span class="meta-chip">&#128197; {e(h['createdDate'])}</span>
      </div>
    </div>
    <div class="h-right">
      {_b(badges['priority'])}
      {_b(badges['classification'])}
      {_b(badges['status'])}
    </div>
  </div>"""

    # ── metrics ───────────────────────────────────────────────────────────────
    metric_boxes = ""
    for m in c["metrics"]:
        val_style = ""
        if m.get("valueColor"):
            val_style += f"color:{e(m['valueColor'])};"
        if m.get("valueFontSize"):
            val_style += f"font-size:{e(m['valueFontSize'])};padding-top:4px;"
        style_attr = f' style="{val_style}"' if val_style else ""
        metric_boxes += f"""
    <div class="metric">
      <div class="metric-label">{e(m['label'])}</div>
      <div class="metric-val"{style_attr}>{e(m['value'])}</div>
      <div class="metric-sub">{e(m.get('sub') or '')}</div>
    </div>"""
    metrics_html = f'<div class="grid4">{metric_boxes}\n  </div>'

    # ── issue classification ──────────────────────────────────────────────────
    ic = c["issueClassification"]
    tag_chips = "".join(f'<span class="tag">{e(t)}</span>' for t in ic["tags"]) or '<span class="tag">none</span>'
    bug_ref_row = (
        _kv("Bug reference", e(ic["bugReference"]) + (" " + _b(ic["bugConfirmationBadge"]) if ic.get("bugConfirmationBadge") else ""))
        if ic.get("bugReference") else ""
    )
    issue_html = f"""
    <div class="card">
      <div class="card-title">Issue classification</div>
      {_kv("Classification", _b(ic['classificationBadge']))}
      {_kv("Origin", e(ic['origin']))}
      {_kv("Root cause", e(ic['rootCause']))}
      {bug_ref_row}
      {_kv("Deployment type", e(ic['deploymentType']))}
      {_kv("Deployment context", e(ic['deploymentContext']))}
      {_kv("Version risk", e(ic['versionRisk']))}
      <hr/>
      {_kv("Tags", "")}
      <div class="tag-row">{tag_chips}</div>
    </div>"""

    # ── resolution timeline ───────────────────────────────────────────────────
    steps = c.get("resolutionTimeline") or []
    if steps:
        steps_html = "".join(
            f'<div class="step">'
            f'<span class="step-num">{e(s["step"])}</span>'
            f'<span class="step-text">{e(s["description"])}</span>'
            f'<span class="step-date">{e(s["date"])}</span>'
            f'</div>'
            for s in steps
        )
    else:
        steps_html = '<div style="font-size:12px;color:#888780;padding:8px 0">Timeline generated on next agent run.</div>'
    timeline_html = f"""
    <div class="card">
      <div class="card-title">Resolution timeline</div>
      {steps_html}
    </div>"""

    # ── support actions ───────────────────────────────────────────────────────
    sa = c["supportActions"]
    left_rows = "".join(_kv_row(r) for r in sa["left"])
    right_rows = "".join(_kv_row(r) for r in sa["right"])
    support_html = f"""
  <div class="card">
    <div class="card-title">Support actions</div>
    <div class="grid2" style="margin-bottom:0">
      <div>{left_rows}</div>
      <div>{right_rows}</div>
    </div>
  </div>"""

    # ── customer signals ──────────────────────────────────────────────────────
    cs = c["customerSignals"]
    evidence_html = "".join(
        f'<div class="signal-row"><span class="signal-icon">&#8220;</span>'
        f'<span class="signal-text">{e(ev)}</span></div>'
        for ev in cs["evidence"]
    ) or '<div style="font-size:12px;color:#888780">No explicit signals captured</div>'
    customer_html = f"""
    <div class="card">
      <div class="card-title">Customer signals</div>
      {_kv("Mood", _b(cs['moodBadge']))}
      {_kv("Reason", e(cs['reason']))}
      {_kv("Escalation risk", e(cs['escalationRisk']))}
      {_kv("Business impact", e(cs['businessImpact']))}
      <hr/>
      <div style="font-size:11px;color:#888780;margin-bottom:6px;font-weight:600">SENTIMENT EVIDENCE</div>
      {evidence_html}
    </div>"""

    # ── product signals ───────────────────────────────────────────────────────
    ps = c["productSignals"]
    sec = ps["section"]
    if sec.get("sectionLabel") and sec.get("rows"):
        prod_rows_html = (
            f'<div style="font-size:11px;color:#888780;margin-bottom:6px;font-weight:600">{e(sec["sectionLabel"])}</div>'
            + "".join(_kv_row(r) for r in sec["rows"])
        )
    else:
        prod_rows_html = '<div style="font-size:12px;color:#888780;margin-bottom:10px">No product pain points identified</div>'

    gaps_html = ""
    if ps.get("gaps"):
        gaps_html = (
            '<hr/><div style="font-size:11px;color:#888780;margin-bottom:6px;font-weight:600">GAPS IDENTIFIED</div>'
            + "".join(
                f'<div class="gap-row"><span class="gap-icon">&#9651;</span>'
                f'<span class="gap-text">{e(g)}</span></div>'
                for g in ps["gaps"]
            )
        )
    product_html = f"""
    <div class="card">
      <div class="card-title">Product signals</div>
      {prod_rows_html}
      {gaps_html}
    </div>"""

    # ── escalation & internal ─────────────────────────────────────────────────
    ei = c["escalationInternal"]
    esc_type_row = (_kv("Escalation type", _b(ei["escalationTypeBadge"]))) if ei.get("escalationTypeBadge") else ""
    note = ei["internalNote"]
    note_date_html = f'<div class="internal-note-meta">{e(note["date"])}</div>' if note.get("date") else ""
    escalation_html = f"""
    <div class="card">
      <div class="card-title">Escalation &amp; internal</div>
      {_kv("Escalated", e(ei['escalated']))}
      {esc_type_row}
      {_kv("Who involved", e(ei['whoInvolved']))}
      <div class="internal-note">
        <div class="internal-note-text">{e(note['text'])}</div>
        {note_date_html}
      </div>
    </div>"""

    # ── context flags ─────────────────────────────────────────────────────────
    flags_html = "".join(
        f'<div class="flag {"flag-true" if f["active"] else "flag-false"}">'
        f'<span class="{"dot-true" if f["active"] else "dot-false"}"></span>'
        f'{e(f["label"])}</div>'
        for f in c["contextFlags"]
    )
    context_html = f"""
    <div class="card">
      <div class="card-title">Context flags</div>
      <div class="flag-grid">{flags_html}</div>
    </div>"""

    # ── case health & recommended action ─────────────────────────────────────
    ch = c["caseHealth"]
    health_html = f"""
  <div class="card" style="margin-bottom:0">
    <div class="card-title">Case health &amp; recommended action</div>
    <div class="grid2" style="margin-bottom:0">
      <div>
        {_kv("Health score", _b(ch['healthBadge']))}
        {_kv("Repeat issue", e(ch['repeatIssue']))}
        {_kv("Jira / SRE", e(ch['jiraSre']))}
        {_kv("TIF", e(ch['tif']))}
      </div>
      <div>
        <div class="action-box">
          <div class="action-label">Recommended action</div>
          <div class="action-text">{e(ch['recommendedAction'])}</div>
        </div>
      </div>
    </div>
  </div>"""

    # ── footer ────────────────────────────────────────────────────────────────
    f = c["footer"]
    footer_html = f"""
  <div class="footer">
    <span class="footer-text">{e(f['left'])}</span>
    <span class="footer-text">{e(f['right'])}</span>
  </div>"""

    case_num = c["meta"].get("caseNumber", "")
    account = c["header"].get("accountName", "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Case {e(case_num)} — {e(account)} — Insight Card</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
{header_html}
{metrics_html}
  <div class="grid2">
{issue_html}
{timeline_html}
  </div>
{support_html}
  <div class="grid2">
{customer_html}
{product_html}
  </div>
  <div class="grid2">
{escalation_html}
{context_html}
  </div>
{health_html}
{footer_html}
</div>
</body>
</html>"""
