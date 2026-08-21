import argparse
import json
import re

from .template import render_card
from .transform import to_card_json


def main():
    parser = argparse.ArgumentParser(description="Render case analysis JSON as HTML insight card")
    parser.add_argument("analysis", help="Path to case analysis JSON (raw agent output)")
    parser.add_argument("-o", "--output", default=None, help="Output HTML path")
    parser.add_argument("--json-only", action="store_true", help="Only write card JSON, skip HTML")
    args = parser.parse_args()

    with open(args.analysis, encoding="utf-8") as fh:
        data = json.load(fh)

    a = data.get("analysis", data)
    base = re.sub(r"\.json$", "", args.analysis)

    card = to_card_json(a)

    card_path = base + "_card.json"
    with open(card_path, "w", encoding="utf-8") as fh:
        json.dump(card, fh, indent=2, ensure_ascii=False)
    print(f"Card JSON : {card_path}")

    if not args.json_only:
        html_out = render_card(card)
        html_path = args.output or base + ".html"
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(html_out)
        print(f"HTML card : {html_path}")


if __name__ == "__main__":
    main()
