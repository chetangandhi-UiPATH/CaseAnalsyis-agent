# CIP Case Analysis Agent

A UiPath Coded Agent (LangGraph) that pulls a Salesforce support case, analyses it with an
LLM, and produces a structured "CIP_CaseAnalysis" JSON — the same data model used to power
manager snapshots, account health, and support-quality reporting.

## What it does

Given a Salesforce case number, the agent:

1. **Fetches the case** from Salesforce — case fields, email thread, internal case comments,
   and Chatter feed (`case_analysis/salesforce.py`), trimming long email/comment bodies so
   the payload stays within the LLM's context budget.
2. **Runs two LLM analyses in parallel** over that raw case data (`case_analysis/graph.py`):
   - **Case Classifier** — technical classification (what broke, product/version, deployment
     type), product-bug confirmation gating, linked SRE/ER/TIF/Jira tickets, version risk,
     case health, context tags, and a 4–7 step resolution timeline.
   - **Communication & Sentiment Analyzer** — latest email, action owner, call status,
     internal discussion (CaseComments/Chatter), customer sentiment and its trajectory,
     product feedback, and support-quality pain points.
3. **Synthesizes the result** (`synthesizer` node) by merging both LLM outputs with facts
   computed directly from Salesforce data — no LLM involved for these:
   - case metadata (id, subject, status, owner, dates)
   - case age, initial-response delay, email back-and-forth count
   - product generation (Act-1 vs Act-2) from a fixed lookup table
   - linked tickets built from `Jira_Key__c` / child ER-TIF-SRE cases
   - `caseSummary` — composed from the two LLM outputs' `issue_summary` /
     `resolution_summary` / `nextAction` fields rather than asked of the LLM a third time

**Only 2 LLM calls per case run** (down from an earlier 5–6-call version — see the comment
in `graph.py`). Everything that can be derived deterministically from Salesforce data is
computed in code, not asked of the model, which keeps cost down and removes a class of
possible hallucination.

All prompts (`case_analysis/prompts/`) share a common guardrail block (`shared.py`): only
populate fields the data explicitly supports, never invent names/dates/tier labels, and use
role/entity labels instead of individual names.

## Output

The agent returns `{"analysis": {...}}` (or `{"error": "..."}` on failure). `analysis` is a
flat JSON object — the CIP_CaseAnalysis schema — containing fields such as:

- **Classification**: `classification`, `issueOrigin`, `rootCause`, `bugConfirmationStatus`,
  `bugReference`, `deployment`, `product`, `productGeneration`, `version_risk`
- **Tickets**: `linked_tickets`, `sre_dependency`, `tif_dependency`, `tif_ticket`, `jiraUpdate`
- **Case state**: `caseAge`, `caseHealth`, `isEscalated`, `cloud_outage`, `tags`
- **Timeline**: `resolution_timeline` (4–7 chronological milestones)
- **Communication**: `latestEmail`, `actionOwner`, `callStatus`, `internalDiscussion`,
  `nextAction`, `communicationPattern`
- **Sentiment**: `customerMood`, `sentimentTrend`, `sentiment_evidence`, `businessImpact`
- **Product/support quality**: `pain_points`, `productSpecificFeedback`,
  `support_improvements`, `supportPainPoints`, `logRequestPattern`, `delaysUipath`,
  `delaysCustomer`
- **Deterministic fields**: `caseId`, `caseNumber`, `accountId`, `accountName`, `subject`,
  `status`, `owner`, `caseCreatedDate`, `caseAge`, `emailExchangeCount`,
  `backAndForthCount`, `initialResponseDelay`, `caseSummary`

This raw output can be transformed into a presentation-ready **insight card JSON**
(`case_analysis/render/`) — the same object grouped into header/metrics/timeline/signals
sections with display labels, badge colors, and truncated text pre-computed, ready for a UI
to render directly without re-deriving anything.

An optional **reviewer** (`case_analysis/reviewer/`) re-checks a finished analysis against
the guardrail rules (hallucination, field drift, closed-case wording, bug-confirmation
gating, sentiment consistency, etc.) and reports violations as structured flags.

## Running it

### Prerequisites

- `uip login` completed at least once (the agent needs a fresh UiPath access token to call
  the LLM Gateway).
- A `.env` file in this directory with:
  ```
  SF_INSTANCE_URL=https://<your-instance>.my.salesforce.com
  SF_ACCESS_TOKEN=<salesforce access token>
  UIPATH_URL=...
  UIPATH_ORGANIZATION_ID=...
  UIPATH_TENANT_ID=...
  UIPATH_MODEL_NAME=...
  ```
- Python 3.11+ and `uv` installed; dependencies come from `pyproject.toml`.

### Quick start

```bash
./run.sh '{"case_number": "02844965"}'
```

This will:
1. Refresh the UiPath access token (`uip login refresh`).
2. Inject `sf_instance_url` / `sfdc_access_token` from `.env` into the input if not already
   supplied.
3. Run the agent (`uipath run agent '<input-json>'`) and save the raw output to
   `last_output.json`.
4. Always build the insight-card JSON alongside it (`last_output_card.json`).

**Options:**

```bash
./run.sh '{"case_number": "02844965"}' --output my_output.json   # custom output filename
./run.sh '{"case_number": "02844965"}' --review                  # also run the guardrail reviewer
```

### Running the pieces directly

```bash
# Run the agent via the UiPath CLI directly (bypassing run.sh's token/env wiring)
uv run uipath run main.py '{"case_number": "02844965", "sf_instance_url": "...", "sfdc_access_token": "..."}'

# Build the insight-card JSON from an existing analysis output
uv run python -m case_analysis.render.cli last_output.json

# Review an existing analysis output against the guardrail rules
uv run python -m case_analysis.reviewer.cli --analysis last_output.json --case-data raw_case.json
```

### Evaluating

```bash
uv run uipath eval
```

Runs the project's evaluation set (auto-discovered) against the agent.
