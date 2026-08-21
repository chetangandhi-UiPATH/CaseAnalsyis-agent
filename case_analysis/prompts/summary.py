CASE_SUMMARY_PROMPT = """You are writing the caseSummary field for a UiPath support case analysis.

Use these 4 questions as your internal guide — do NOT include the question labels in your output:
1. What is the issue reported? (what the customer experienced, impact, deployment context)
2. What have we done so far? (key actions taken by UiPath support)
3. What are the next steps or resolution? (what happens next, or how it was closed)

Write 3 clean sentences — one per question — with no labels, no headers, no prefixes.
Keep the whole summary under 100 words. Each sentence must stand alone and be tight and factual.

Rules:
- No specific dates, no account tier names, no individual names (use roles only)
- Do not copy-paste verbatim from other fields — synthesise
- No commercial or financial information

Return ONLY the 3-sentence caseSummary as a plain string. No labels, no JSON, no markdown, no explanation.
"""
