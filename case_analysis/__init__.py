"""CIP Case Analysis — Salesforce support case analyser.

Package layout:
  graph.py          LangGraph state machine (entrypoint: `graph`)
  llm_utils.py       Shared LLM client + JSON-extraction helpers
  deterministic.py    Pure-Python computations (tickets, dates, email metrics) — never LLM-derived
  salesforce.py         Salesforce REST/SOQL client
  prompts/                The 2 LLM prompts run by the graph
  render/                   Insight-card JSON builder
  reviewer/                   Guardrail-violation reviewer for analysis output
"""
