"""CLI: python -m src.main --case case_01 [--all]."""
from __future__ import annotations

import argparse
import json

from src.agent.runner import CASES_IN, CASES_OUT, run_all, run_case


def main() -> None:
    ap = argparse.ArgumentParser(description="fraud-agent investigation CLI")
    ap.add_argument("--case", default="", help="case id e.g. case_01")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.all:
        outs = run_all()
        print(json.dumps({"ran": len(outs), "out_dir": str(CASES_OUT)}, indent=1))
    elif args.case:
        print(json.dumps(run_case(args.case), indent=1))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
