"""CLI entrypoint invoked by run.sh ("uv run python render.py <file>") — kept
as a thin shim so run.sh stays unchanged; the implementation lives in
case_analysis/render/.
"""
from case_analysis.render.cli import main

if __name__ == "__main__":
    main()
