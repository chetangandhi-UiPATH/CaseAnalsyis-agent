"""Case Analysis insight-card JSON builder.

to_card_json(analysis) transforms the flat agent-output JSON into a
card-aligned JSON — all display values pre-computed, ready to hand to
whatever downstream tool (or UI) presents it.
"""
from .transform import to_card_json

__all__ = ["to_card_json"]
