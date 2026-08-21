import argparse
import json

from .core import review


def _print_report(result: dict) -> None:
    total = result.get("totalFlags", 0)
    case = result.get("caseNumber", "unknown")

    print(f"\n{'='*60}")
    print(f"  Reviewer Report — Case {case}")
    print(f"  Total flags: {total}")
    print(f"{'='*60}\n")

    flags = result.get("flags", [])
    if not flags:
        print("  No violations found.\n")
    else:
        for i, f in enumerate(flags, 1):
            sev = f.get("severity", "").upper()
            rule = f.get("rule", "")
            field = f.get("field", "")
            issue = f.get("issue", "")
            value = f.get("value", "")
            print(f"  [{i}] {rule} | {sev} | {field}")
            print(f"      Issue : {issue}")
            if value:
                print(f"      Value : {value[:120]}")
            print()

    print(f"  Summary: {result.get('summary', '')}\n")


def main():
    parser = argparse.ArgumentParser(description="Review a CIP_CaseAnalysis output for guardrail violations.")
    parser.add_argument("--analysis", required=True, help="Path to the analysis JSON output file")
    parser.add_argument("--case-data", help="Path to the raw Salesforce case JSON file (optional but recommended)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted report")
    args = parser.parse_args()

    with open(args.analysis) as f:
        raw = json.load(f)

    # uipath run --output-file wraps output as {"analysis": {...}, "error": ...}
    analysis = raw.get("analysis", raw) if isinstance(raw, dict) and "analysis" in raw else raw

    case_data = None
    if args.case_data:
        with open(args.case_data) as f:
            case_data = json.load(f)

    result = review(analysis, case_data)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_report(result)


if __name__ == "__main__":
    main()
