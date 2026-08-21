"""Entrypoint referenced by langgraph.json ("./main.py:graph") — kept as a thin
shim so the deployment binding stays unchanged while the actual implementation
lives in the case_analysis package.
"""
from case_analysis.graph import graph

__all__ = ["graph"]
