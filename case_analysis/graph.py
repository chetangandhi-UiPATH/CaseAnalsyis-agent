import json
from typing import Optional

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from .deterministic import (
    build_linked_tickets,
    compute_case_age,
    compute_communication_metrics,
    compose_case_summary,
    product_generation,
)
from .llm_utils import make_analysis_node
from .prompts import CASE_CLASSIFICATION_PROMPT, COMMUNICATION_SENTIMENT_PROMPT
from .salesforce import fetch_case


class GraphState(BaseModel):
    case_number: str
    sf_instance_url: str
    sfdc_access_token: str
    raw_case_data: Optional[str] = None
    classification_result: Optional[dict] = None
    communication_result: Optional[dict] = None
    analysis: Optional[dict] = None
    error: Optional[str] = None


class GraphOutput(BaseModel):
    analysis: Optional[dict] = None
    error: Optional[str] = None


async def fetch_case_data(state: GraphState) -> dict:
    try:
        case = await fetch_case(state.case_number, state.sf_instance_url, state.sfdc_access_token)
        return {"raw_case_data": json.dumps(case, default=str)}
    except Exception as exc:
        return {"error": str(exc)}


# Two calls total: each of these used to be its own LLM call re-sending the
# full case payload independently (5 calls originally). A third call used to
# generate caseSummary from the merged result — replaced below with a
# deterministic composition of fields these two calls already produce, since
# it was mostly re-deriving the same content in different words.
case_classifier = make_analysis_node(
    CASE_CLASSIFICATION_PROMPT,
    "Classify this case, tag it with context indicators, and extract its resolution timeline. "
    "Return the combined JSON described in the Output Format.",
    "classification_result",
)
communication_analyzer = make_analysis_node(
    COMMUNICATION_SENTIMENT_PROMPT,
    "Analyse the support communication, action ownership, customer sentiment, and support quality "
    "in this case. Return the combined JSON described in the Output Format.",
    "communication_result",
)


def synthesizer(state: GraphState) -> dict:
    if state.error:
        return {}

    raw = json.loads(state.raw_case_data)

    # Merge both partial results — each writes to distinct fields, no conflicts
    merged = {}
    for partial in [state.classification_result, state.communication_result]:
        if partial:
            merged.update({k: v for k, v in partial.items() if not k.startswith("_error")})
    merged.setdefault("resolution_timeline", [])

    # Salesforce metadata fields — sourced directly, no LLM involved
    merged.update({
        "caseId": raw.get("Id", "NA"),
        "caseNumber": raw.get("CaseNumber", state.case_number),
        "accountId": raw.get("AccountId") or (raw.get("Account") or {}).get("Id", "NA"),
        "accountName": (raw.get("Account") or {}).get("Name", "NA"),
        "subject": raw.get("Subject", "NA"),
        "status": raw.get("Status", "NA"),
        "priority": raw.get("Priority", "NA"),
        "owner": (raw.get("Owner") or {}).get("Name", "NA"),
        "caseCreatedDate": raw.get("CreatedDate", "NA"),
        "caseClosedDate": raw.get("ClosedDate") or "",
    })
    computed_age = compute_case_age(raw)
    if computed_age:
        merged["caseAge"] = computed_age

    merged.update(compute_communication_metrics(raw))
    merged["productGeneration"] = product_generation(merged.get("product"))

    tickets = build_linked_tickets(raw)
    if tickets:
        merged["linked_tickets"] = tickets

    merged["caseSummary"] = compose_case_summary(merged)

    # Job tracking fields — populated by Orchestrator at runtime
    merged.update({
        "jobId": "NA",
        "jobRunDate": "YYYY-MM-DDT00:00:00.000+0000",
        "createdOn": "YYYY-MM-DDT00:00:00.000+0000",
        "lastModifiedOn": "YYYY-MM-DDT00:00:00.000+0000",
    })

    return {"analysis": merged}


builder = StateGraph(GraphState, output=GraphOutput)
builder.add_node("fetch_case_data", fetch_case_data)
builder.add_node("case_classifier", case_classifier)
builder.add_node("communication_analyzer", communication_analyzer)
builder.add_node("synthesizer", synthesizer)

# Fan-out: both analysis calls run in parallel after fetch
builder.add_edge(START, "fetch_case_data")
builder.add_edge("fetch_case_data", "case_classifier")
builder.add_edge("fetch_case_data", "communication_analyzer")

# Fan-in: synthesizer waits for both before running
builder.add_edge("case_classifier", "synthesizer")
builder.add_edge("communication_analyzer", "synthesizer")

builder.add_edge("synthesizer", END)

graph = builder.compile()
