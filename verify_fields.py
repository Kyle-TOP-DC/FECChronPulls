#!/usr/bin/env python3
"""
Field verifier for fec_tracker.py
=================================

Hits each FEC endpoint the tracker relies on ONCE and checks that every field the
tracker reads actually exists in the response. Run this before turning on the
schedule so you catch any field-name drift up front.

Usage:
    pip install requests
    export FEC_API_KEY=yourkey            # DEMO_KEY works but is rate-limited
    python verify_fields.py               # uses the default sample committees
    python verify_fields.py C00923417 C30003586   # IE sample, EC sample

Exit code is 0 if all required fields were found, 1 if any are missing or no
sample records were available to check.
"""

import datetime as dt
import os
import sys

import requests

FEC_API_KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")
CYCLE = int(os.environ.get("FEC_CYCLE", "2026"))
BASE = "https://api.open.fec.gov/v1"

# Defaults: an IE super PAC with recent activity, and the electioneering filer.
IE_SAMPLE = sys.argv[1] if len(sys.argv) > 1 else "C00923417"   # Think Big
EC_SAMPLE = sys.argv[2] if len(sys.argv) > 2 else "C30003586"   # Public First Action Inc.

# Fields the tracker reads, per endpoint. "any" groups = at least one must exist.
CHECKS = {
    "committee_totals": {
        "required": ["receipts", "independent_expenditures", "disbursements",
                     "last_cash_on_hand_end_period", "coverage_end_date"],
    },
    "schedule_e_efile": {
        "required": ["expenditure_amount"],
        "any": [["committee_id", "filer_committee_id_number"]],
        "nice": ["transaction_id", "file_number", "line_number"],
    },
    "efile_filings": {
        "required": ["file_number", "form_type"],
        "nice": ["receipt_date", "committee_id", "pdf_url", "fec_url"],
    },
    "electioneering": {
        "required": ["calculated_candidate_share"],
        "nice": ["sub_id", "candidate_id", "disbursement_amount"],
    },
}

GREEN, RED, YELLOW, DIM, RESET = (
    "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
)


def fec_get(path, **params):
    params["api_key"] = FEC_API_KEY
    r = requests.get(f"{BASE}{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def first_record(path, **params):
    """Return (record, total_count) for the first result, or (None, count)."""
    data = fec_get(path, **params)
    results = data.get("results", [])
    count = (data.get("pagination") or {}).get("count")
    return (results[0] if results else None), count


def truncate(v, n=48):
    s = str(v)
    return s if len(s) <= n else s[:n] + "…"


def report(name, path, record, count):
    spec = CHECKS[name]
    print(f"\n{'='*70}\n{name}  →  {path}")
    if record is None:
        print(f"{YELLOW}  No records returned (count={count}). "
              f"Can't verify fields — try a different committee or widen the "
              f"date window, then re-run.{RESET}")
        return False

    print(f"{DIM}  {count if count is not None else '?'} record(s) available; "
          f"inspecting the first.{RESET}")
    keys = set(record.keys())
    ok = True

    for f in spec.get("required", []):
        present = f in keys
        mark = f"{GREEN}OK{RESET}" if present else f"{RED}MISSING{RESET}"
        val = f"{DIM}= {truncate(record.get(f))}{RESET}" if present else ""
        print(f"  [{mark}] required: {f} {val}")
        ok = ok and present

    for group in spec.get("any", []):
        hit = [f for f in group if f in keys]
        mark = f"{GREEN}OK{RESET}" if hit else f"{RED}MISSING{RESET}"
        detail = (f"{DIM}(found {', '.join(hit)}){RESET}" if hit
                  else f"{DIM}(none of {', '.join(group)}){RESET}")
        print(f"  [{mark}] one-of: {' / '.join(group)} {detail}")
        ok = ok and bool(hit)

    for f in spec.get("nice", []):
        present = f in keys
        mark = f"{GREEN}OK{RESET}" if present else f"{YELLOW}absent{RESET}"
        val = f"{DIM}= {truncate(record.get(f))}{RESET}" if present else ""
        print(f"  [{mark}] optional: {f} {val}")

    print(f"{DIM}  all keys: {', '.join(sorted(keys))}{RESET}")
    return ok


def main():
    print(f"FEC field verifier — key={'DEMO_KEY' if FEC_API_KEY=='DEMO_KEY' else 'set'}, "
          f"cycle={CYCLE}\nIE sample={IE_SAMPLE}  EC sample={EC_SAMPLE}")
    min_date = (dt.date.today() - dt.timedelta(days=120)).isoformat()
    results = []

    try:
        rec, cnt = first_record(f"/committee/{IE_SAMPLE}/totals/",
                                cycle=CYCLE, per_page=1)
        results.append(report("committee_totals",
                              f"/committee/{IE_SAMPLE}/totals/", rec, cnt))
    except Exception as e:
        print(f"{RED}committee_totals request failed: {e}{RESET}")
        results.append(False)

    try:
        rec, cnt = first_record("/schedules/schedule_e/efile/",
                                committee_id=IE_SAMPLE, min_date=min_date, per_page=1)
        # If the 4-month efile window is empty, fall back to processed Schedule E
        # so you can still confirm field names.
        if rec is None:
            print(f"{YELLOW}  efile window empty; probing processed "
                  f"/schedules/schedule_e/ instead…{RESET}")
            rec, cnt = first_record("/schedules/schedule_e/",
                                    committee_id=IE_SAMPLE, cycle=CYCLE, per_page=1)
        results.append(report("schedule_e_efile",
                              "/schedules/schedule_e/efile/", rec, cnt))
    except Exception as e:
        print(f"{RED}schedule_e request failed: {e}{RESET}")
        results.append(False)

    try:
        rec, cnt = first_record("/efile/filings/",
                                committee_id=IE_SAMPLE, per_page=1, sort="-receipt_date")
        results.append(report("efile_filings", "/efile/filings/", rec, cnt))
    except Exception as e:
        print(f"{RED}efile_filings request failed: {e}{RESET}")
        results.append(False)

    try:
        rec, cnt = first_record("/electioneering/",
                                committee_id=EC_SAMPLE, cycle=CYCLE, per_page=1)
        results.append(report("electioneering", "/electioneering/", rec, cnt))
    except Exception as e:
        print(f"{RED}electioneering request failed: {e}{RESET}")
        results.append(False)

    print(f"\n{'='*70}")
    if all(results):
        print(f"{GREEN}All required fields verified. The tracker's mappings are good.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}Some checks failed or had no data (see above). "
              f"Fix field names in fec_tracker.py or re-run when filings exist.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
