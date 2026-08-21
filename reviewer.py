"""CLI entrypoint invoked by run.sh ("python reviewer.py --analysis <file>") —
kept as a thin shim so run.sh stays unchanged; the implementation lives in
case_analysis/reviewer/.
"""
from case_analysis.reviewer.cli import main

if __name__ == "__main__":
    main()
