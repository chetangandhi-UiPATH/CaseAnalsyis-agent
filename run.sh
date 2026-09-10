#!/usr/bin/env bash
# Run the case-analysis agent locally, save output, and optionally review it.
#
# Usage:
#   ./run.sh '{"case_number": "02844965"}'
#   ./run.sh '{"case_number": "02844965"}' --review
#   ./run.sh '{"case_number": "02844965"}' --output my_output.json
#   ./run.sh '{"case_number": "02844965"}' --output my_output.json --review

set -euo pipefail

CASE_INPUT=""
OUTPUT_FILE="last_output.json"
RUN_REVIEW=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --review) RUN_REVIEW=true; shift ;;
    --output) OUTPUT_FILE="$2"; shift 2 ;;
    *) CASE_INPUT="$1"; shift ;;
  esac
done

if [[ -z "$CASE_INPUT" ]]; then
  echo "Usage: $0 '{\"case_number\": \"<NUMBER>\"}' [--output file.json] [--review]"
  exit 1
fi

echo "Refreshing UiPath access token..."
SESSION=$(uip login refresh 2>/dev/null)
TOKEN=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['Data']['AccessToken'])" 2>/dev/null)

if [[ -z "$TOKEN" ]]; then
  echo "Error: could not refresh token. Run 'uip login' first."
  exit 1
fi

source .venv/bin/activate

source .env 2>/dev/null || true

# Inject SF credentials from .env into the input JSON
FULL_INPUT=$(python3 -c "
import json, sys
data = json.loads(sys.argv[1])
data.setdefault('sf_instance_url', '${SF_INSTANCE_URL}')
data.setdefault('sfdc_access_token', '${SF_ACCESS_TOKEN}')
print(json.dumps(data))
" "$CASE_INPUT")

echo "Running agent..."
UIPATH_ACCESS_TOKEN="$TOKEN" uipath run agent "$FULL_INPUT" --output-file "$OUTPUT_FILE"

echo ""
echo "Output saved to: $OUTPUT_FILE"

# Always build the insight-card JSON
echo "Building insight card JSON..."
uv run python render.py "$OUTPUT_FILE"

if [[ "$RUN_REVIEW" == true ]]; then
  echo ""
  echo "Running reviewer..."
  python reviewer.py --analysis "$OUTPUT_FILE"
fi
