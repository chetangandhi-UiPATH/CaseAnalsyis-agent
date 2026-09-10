import argparse
import json
import re

from .transform import to_card_json


def main():
    parser = argparse.ArgumentParser(description="Build the case-analysis insight-card JSON from agent output")
    parser.add_argument("analysis", help="Path to case analysis JSON (raw agent output)")
    parser.add_argument("-o", "--output", default=None, help="Output card JSON path")
    args = parser.parse_args()

    with open(args.analysis, encoding="utf-8") as fh:
        data = json.load(fh)

    a = data.get("analysis", data)
    base = re.sub(r"\.json$", "", args.analysis)

    card = to_card_json(a)

    card_path = args.output or base + "_card.json"
    with open(card_path, "w", encoding="utf-8") as fh:
        json.dump(card, fh, indent=2, ensure_ascii=False)
    print(f"Card JSON : {card_path}")


if __name__ == "__main__":
    main()
