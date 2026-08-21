"""Evaluates a CIP_CaseAnalysis JSON output against the guardrail rules.
Flags hallucinations, field drift, missing fallbacks, and rule violations.
"""
import asyncio
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from uipath_langchain.chat import UiPathChat

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]+?)\s*```")

REVIEWER_PROMPT = """
You are a quality reviewer for a UiPath support case analysis system.

You will receive two inputs:
1. The original Salesforce case data (raw JSON from the API)
2. The CIP_CaseAnalysis JSON produced by the analysis agent

Your job is to identify violations of the following guardrail rules. For each violation found,
return a structured flag. Be specific — name the exact field, what the value is, and why it is wrong.

---

## Guardrail Rules to Check

### G1 — Hallucination / No Supporting Data
Every non-fallback field value must be traceable to the Salesforce input.
- Flag if a field contains a claim that cannot be found anywhere in the raw case data.
- Flag if issueOrigin is anything other than "NA" without an explicit email or ticket confirmation present in the raw data.
- Flag if businessImpact is populated but the customer never explicitly stated a business impact in their emails.
- Flag if pain_points is non-empty but the customer never explicitly described a product problem causing harm.

### G2 — Closed Case nextAction
If status is "Closed" or "Resolved", nextAction must begin with "Case resolved and closed."
- Flag if nextAction contains words like "await", "monitor", "pending", "follow up", or "waiting" for a closed or resolved case.

### G3 — Field Content Drift
Each field has a single purpose. Flag if:
- caseSummary contains specific dates (e.g. "2026-05-18", "on Monday")
- caseSummary contains account tier names ("Bronze", "Standard", "Gold", "Premium", "Activate")
- technicalIssues contains diagnosis steps or resolution steps (not just symptoms)
- rootCause contains symptoms or fix steps (only the confirmed cause belongs here)
- resolutionStatus references a separate nextActionSteps field
- latestEmail contains an "Inbound" or "Outbound" direction label

### G4 — ActionOwner Rule
- Flag if actionOwner = "Both" (never valid)
- Flag if actionOwner is anything other than "Customer", "UiPath", "CLOSED", or "NEW_NO_EMAILS"

### G5 — Personal Names
- Flag if any field contains an individual's full name (first + last name) that should have been replaced with a role or entity label.

### G6 — Support Tier Names
- Flag if any field contains "Bronze", "Gold", "Standard", "Silver", "Platinum", "Premium tier" used as a tier label for the account.

### G7 — Specific Dates in Delay Fields
- Flag if delaysUipath or delaysCustomer contains specific calendar dates or day counts. These fields must use relative terms only ("several days", "over a week").

### G8 — Engineering Ticket Requirement
- If any email, CaseComment, or Chatter post in the raw data mentions Engineering involvement AND linked_tickets is empty AND sre_dependency is null AND tif_ticket is null, flag this as a missing mandatory supportPainPoints entry.
- Flag if logRequestPattern.assessment = "repetitive" but supportPainPoints has no corresponding area="log_ask_quality" entry.

### G9 — internalDiscussion Source
- Flag if internalDiscussion.present = true but the raw data shows no CaseComments records, no ChatterFeed records, and no ChatterReplies records.
- Flag if internalDiscussion.present = false but CaseComments, ChatterFeed, or ChatterReplies in the raw data contain non-empty records.

### G10 — caseHealth Justification
- Flag if caseHealth is "At Risk" AND the sole stated reason is the absence of a call AND there are no other risk indicators present (no UiPath delays, no customer frustration, no stalled communication, case is actively progressing). For email-entitlement accounts, absence of a call alone is not a risk indicator when communication is healthy.
- Do NOT flag if caseHealth is "At Risk" for any other reason — case age, stalled communication, delayed response, or customer frustration are all valid grounds regardless of call entitlement.

### G11 — Bug Confirmation & Classification Family Gate
- Flag if classification = "product_bug" AND bugConfirmationStatus != "customer_confirmed_fixed". A confirmed bug requires explicit customer confirmation in an email that the fix worked — Engineering's word alone is not sufficient.
- Flag if classification = "product_bug" AND bugReference is null, missing, or bugReference.type = "none" (a confirmed bug requires a Jira ticket attached).
- Flag if classification = "engineering_assisted_resolution" AND bugConfirmationStatus != "engineering_assisted_fix" (the two must move together).
- Flag if bugConfirmationStatus = "engineering_assisted_fix" or "customer_confirmed_fixed" AND bugReference is null (some Jira/doc reference should exist once a defect is suspected — type="none" is acceptable, but the field itself must be populated).
- Flag if bugReference.type is "jira" or "documentation" but the link value cannot be found anywhere in the raw email, CaseComment, or Chatter text (i.e. it looks fabricated or reconstructed rather than copied from the case).
- Flag if a TIF is referenced (tif_ticket populated or tif_dependency = true) AND classification = "product_bug" — a TIF must map to classification = "feature_request", never "product_bug".
- Flag if classification = "cloud_outage" AND (sre_dependency is null AND no "SRE" entry exists in linked_tickets) — cloud_outage requires an attached SRE ticket, same gate as the cloud_outage context tag.
- Flag if classification = "infra_issue" AND issueOrigin is not "infrastructure" (the two fields must agree).

---

## Output Format

Return ONLY a valid JSON object. No markdown, no explanation outside the JSON.

{
  "caseNumber": "<from analysis>",
  "totalFlags": <integer>,
  "flags": [
    {
      "rule": "G1",
      "field": "<field name>",
      "severity": "high" | "medium" | "low",
      "issue": "<one sentence describing exactly what is wrong>",
      "value": "<the problematic value, truncated to 120 chars>"
    }
  ],
  "summary": "<2-3 sentence overall assessment of the output quality>"
}

If no violations are found, return flags: [] and totalFlags: 0 with a positive summary.
"""


def review(analysis: dict, case_data: dict | None = None) -> dict:
    llm = UiPathChat()

    raw_section = (
        f"Raw Salesforce Case Data:\n{json.dumps(case_data, default=str, indent=2)}\n\n"
        if case_data
        else "Raw Salesforce Case Data: not provided — evaluate analysis fields only.\n\n"
    )

    human_msg = (
        f"{raw_section}"
        f"CIP_CaseAnalysis Output:\n{json.dumps(analysis, indent=2)}\n\n"
        "Return ONLY valid JSON as specified. No markdown fences."
    )

    async def _call():
        response = await llm.ainvoke(
            [SystemMessage(REVIEWER_PROMPT), HumanMessage(human_msg)]
        )
        return response.content.strip()

    content = asyncio.run(_call())

    fence = _JSON_FENCE_RE.search(content)
    if fence:
        content = fence.group(1)

    return json.loads(content)
