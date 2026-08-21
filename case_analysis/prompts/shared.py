"""Text blocks shared across multiple prompts — edit once, not per-prompt."""

SHARED = """
**Core Guardrail:** Only populate fields from data explicitly present in the Salesforce input.
If a field has no supporting data, use the appropriate fallback ("NA", null, false, or []).
Present all findings in professional, generic terms — do not invent, infer, or embellish.

## Analysis Principles

**Think Before Analysing:** Do not populate a field based on what seems plausible. Ask: does the
data explicitly support this conclusion? If ambiguous, use the fallback. Confirmation must exist in
an email, ticket, or comment — educated inference is not confirmation.

**Minimum Necessary Detail:** Record only what the data materially supports. Do not inflate entries
to demonstrate thoroughness. Each field has one purpose — fill it, then stop.

**Surgical Observations:** Scope each observation precisely. Do not allow content to drift across
fields. If you find yourself repeating the same information in multiple fields, one is out of scope.

**Evidence-Grounded Output:** Every value must be traceable to a specific data point in the input.
If you cannot identify the source, use a fallback value — not a plausible assumption.

## Standing Rules

- Replace all individual names with their role or organisational entity. UiPath personnel:
  "UiPath clarified…". Customer personnel: the account name or "customer".
- Do not use tier labels (Bronze, Standard, Gold, Premium, Activate). Use "account entitlement".
- If a call was declined or not offered: "call request reviewed against account entitlement".
"""

DEPLOYMENT_REF = """
## Deployment vs Product — Critical Distinction

These are TWO separate concepts and must never be mixed in the same field.

### Deployment Type (infrastructure / hosting — goes in the `deployment` field)

| Value | Meaning | Detection signals |
|-------|---------|-------------------|
| "Automation Cloud" | UiPath-hosted SaaS | cloud.uipath.com, tenant, cloud portal, UiPath-managed infrastructure |
| "Automation Suite" | Customer-managed Kubernetes | Helm, kubectl, ArgoCD, pods, namespaces, cert-manager, cluster_config.json |
| "Standalone" | Customer self-hosted IIS + SQL Server | IIS, AppPool, Windows services, SQL Server, .config files, manual Orchestrator install |
| "Desktop" | No Orchestrator involved — Robot, Studio, or Assistant running locally on an end-user machine | Attended automation, local/unattended execution with no server component, Assistant, Studio Desktop, "my laptop/machine" |

Always pick the closest matching category from the four above — there is no fallback value, so choose
the best fit even when signals are limited.

**Note on "Automation Suite":** "Automation Suite" as a deployment type means the customer is running UiPath products on their own Kubernetes infrastructure. This is NOT the same as "Automation Suite" as a product bundle (see product list below). Detect from infrastructure signals only.

### Product (what the customer is using — goes in the `product` field)

Use the exact product name from this list. A case may involve more than one product — include all affected.

- Integration Service
- Orchestrator
- Studio
- Activities
- Robot
- Automation Suite *(as a product bundle — distinct from the Kubernetes deployment type)*
- Solution Management
- IXP Unstructured Docs
- Agent Builder
- AI Fabric
- Agent Desktop
- Autopilot
- Maestro
- UiPath Insights
- Document Understanding

If the affected product is not in this list, use the closest match or the exact name from the case.

### issueOrigin determination
- Standalone → "customer specific environment" unless a product defect is explicitly confirmed.
- Automation Suite (infra) → verify whether the Helm/Kubernetes layer is customer-managed before attributing to product.
- Automation Cloud → UiPath degradation → "product bug"; firewall/proxy → "customer specific environment".

Always use the exact deployment label from the table above in all text fields (deployment_context_note, nextAction, technicalGuidance).

## Out-of-Support Version Handling

Version risk applies differently by deployment type. Apply the correct rule for the deployment detected:

---

**RULE 1 — Automation Cloud (SaaS / cloud.uipath.com):**
version_risk = false ALWAYS. UiPath manages the platform and keeps it current. Customers on Automation Cloud
do not choose their version. Never set version_risk = true for a cloud-only case.

---

**RULE 2 — On-Premise Standalone Orchestrator or Automation Suite (customer-managed):**
Check the Orchestrator / Automation Suite version in the case. Known out-of-support versions as of 2026:
- 2020.x, 2021.x — end of life
- 22.4.x — LTS, out of support
- 22.10.x — out of support
- 23.4.x — out of support (non-LTS, 6-month support window expired)
- 23.10.x — LTS; borderline — released Oct 2023, 2-year LTS window ended Oct 2025; flag as aging/end-of-support
- 24.10.x and later — currently supported

If the detected version is in the out-of-support list: version_risk = true.

---

**RULE 3 — Robot / Studio (any deployment type):**
Robot and Studio follow a separate release and deprecation timeline from Orchestrator.
- All 2021.x and 22.x Robot/Studio releases — out of support
- 23.4.x Robot/Studio — out of support (non-LTS)
- 23.10.x Robot/Studio — LTS, borderline; flag as aging
- 24.x Robot/Studio — check: non-LTS versions have 6-month support; LTS versions have 2 years
- 25.x and later — currently supported
If the Robot/Studio version is clearly old (any 21.x, 22.x, or 23.4.x): version_risk = true.
For borderline or unlisted versions, note the version in deployment_context_note and recommend checking
https://docs.uipath.com/overview/other/latest/overview/out-of-support-versions for the current timeline.

---

**When version_risk = true (Rules 2 or 3 only):**
1. Set version_risk = true.
2. In deployment_context_note: explicitly state which version is out of support and that upgrading to a currently supported version is recommended.
3. In issue_summary: note the out-of-support version and that the bug/issue may be resolved in supported versions.
4. In productSpecificFeedback: if there is a confirmed product bug AND the customer is on an out-of-support version, include in the workaround field: "This version is out of UiPath support — upgrading is recommended as the issue may be resolved in later releases." Do NOT flag the out-of-support version itself as a product gap.
"""

# Used by both parts of CASE_CLASSIFICATION_PROMPT that touch cloud outages (issue
# classification's `classification` value and context tagging's `cloud_outage` boolean).
# Kept as one block so the two never drift out of sync when edited later.
CLOUD_OUTAGE_GATE = """
Treat a case as a confirmed cloud outage only when BOTH conditions hold:
1. The case's resolution or closure explicitly attributes the issue to a UiPath Cloud platform
   outage — confirmed by UiPath in the thread (e.g. "this was part of a broader platform incident",
   a reference to status.uipath.com, an incident number, or explicit language like "all customers
   affected").
2. An SRE ticket is attached to the case (sre_dependency is non-null, or an "SRE" entry exists in
   linked_tickets).

If the case shows outage-like symptoms — widespread slowness, intermittent platform-wide errors,
"other customers reported the same thing" — but there is **no SRE ticket attached**, this is NOT a
confirmed outage. Use "cloud_performance_issue" instead: this signals a suspected platform-side
performance problem that was never confirmed or formally tracked as an outage.
"""
