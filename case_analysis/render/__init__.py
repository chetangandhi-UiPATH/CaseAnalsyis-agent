"""Case Analysis HTML Insight Card renderer.

Two-step pipeline:
  1. to_card_json(analysis)  →  card dict  (all display values pre-computed, 1-to-1 with HTML)
  2. render_card(card)        →  HTML string (pure template, zero logic)

Every value that appears in the HTML card is a field in the card JSON.
"""
from .template import render_card
from .transform import to_card_json

__all__ = ["to_card_json", "render_card"]
