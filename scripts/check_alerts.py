"""Proactive alerts CLI: run the safety pipeline over a watchlist, print hits.

Usage: python3 scripts/check_alerts.py [--mock]
Demo baseline (no scheduler): exit 0, prints SAFE/CAUTION/UNSAFE per site.
"""

import argparse
import sys

sys.path.insert(0, ".")

WATCHLIST = [
    ("Kochi", 15.0, 74.0),
    ("Chennai", 13.0, 80.2),
    ("Sundarbans", 21.9, 88.9),
]


def main(mock: bool = False) -> int:
    if mock:
        import os

        os.environ["ORCA_LLM_PROVIDER"] = "mock"
    from backend.app.agents import planner

    hits = 0
    for name, lat, lon in WATCHLIST:
        out = planner.answer("Is it safe tomorrow morning?", lat, lon)
        flag = "ALERT" if out.verdict in ("caution", "unsafe") else "ok"
        if flag == "ALERT":
            hits += 1
        print(f"[{out.verdict.upper()}] {name} ({lat},{lon}): {'; '.join(out.reasons)}")
    print(f"{hits} site(s) need attention.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    raise SystemExit(main(ap.parse_args().mock))
