#!/usr/bin/env python3
"""
FEC Super PAC Independent Expenditure Tracker
=============================================

What it does, on every run:
  1. Checks the FEC real-time e-filing feed for each tracked committee and
     detects any NEW filings (24/48-hour IE reports = F24, periodic = F3X, etc.)
     since the last run.
  2. Sends a notification (Slack and/or email) for each new filing.
  3. Pulls each committee's processed cycle totals (money raised + spending)
     and writes a one-row-per-committee snapshot to a Google Sheet
     (with a local CSV fallback if Sheets isn't configured).

Why the split: the FEC's processed data is updated nightly, so totals always
lag ~1 day. The e-filing feed is real-time but only covers the last ~4 months.
We use the real-time feed for ALERTS and processed totals for the SPREADSHEET.

Designed to run unattended on a schedule (see .github/workflows/fec-tracker.yml).
"""

import csv
import datetime as dt
import json
import os
import pathlib
import sys
import time

import requests

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------

# Your FEC API key (free): https://api.open.fec.gov/developers/
# Falls back to DEMO_KEY (heavily rate-limited) so you can smoke-test.
FEC_API_KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")

# Election cycle for totals (even year). 2026 cycle covers 2025-2026.
CYCLE = int(os.environ.get("FEC_CYCLE", "2026"))

# The finite set of super PACs to track: FEC committee_id -> friendly label.
# Find IDs at https://www.fec.gov/data/committees/ or with find_committee() below.
COMMITTEES = {
    "C00916114": "Leading the Future",
    "C00923417": "Think Big",
    "C00916692": "American Mission",
    "C00928374": "Jobs and Democracy PAC",
    "C00928390": "Defending Our Values PAC",
    "C00930503": "Public First",  # super PAC arm of the Public First Action network
    "C30003586": "Public First Action Inc.",  # electioneering-comm filer (see EC_FILERS)
}
# Filers that report ELECTIONEERING COMMUNICATIONS (Form 9), not Schedule E
# independent expenditures. Their spend comes from the /electioneering/ endpoint and
# lands in the `electioneering_comms_spend` column; their `receipts` stay blank
# because such filers (e.g. 501(c)(4)s) don't itemize donors to the FEC.
EC_FILERS = {"C30003586"}
# NOTE — "Build American AI" is a 501(c)(4) with no FEC registration at all, so it
# cannot be tracked here (it files only with the IRS).
# Optional: load committees from an env var (JSON) to avoid editing code.
if os.environ.get("FEC_COMMITTEES"):
    COMMITTEES = json.loads(os.environ["FEC_COMMITTEES"])

BASE = "https://api.open.fec.gov/v1"
STATE_FILE = pathlib.Path(os.environ.get("FEC_STATE_FILE", "seen_filings.json"))
CSV_FALLBACK = pathlib.Path(os.environ.get("FEC_CSV", "super_pac_totals.csv"))
# Web-facing JSON the AI super PAC tracker page can fetch directly.
TOTALS_JSON = pathlib.Path(os.environ.get("FEC_TOTALS_JSON", "totals.json"))

# Notification config (all optional — set the ones you want)
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "")

# Google Sheets config (optional)
SHEET_ID = os.environ.get("SHEET_ID", "")
WORKSHEET = os.environ.get("WORKSHEET", "Totals")
GOOGLE_SA_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")  # full JSON blob


# --------------------------------------------------------------------------
# FEC API CLIENT
# --------------------------------------------------------------------------

def fec_get(path, **params):
    """GET an OpenFEC endpoint with the API key, light retry on 429/5xx."""
    params["api_key"] = FEC_API_KEY
    url = f"{BASE}{path}"
    for attempt in range(4):
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504):
            wait = 2 ** attempt
            print(f"  [retry] {r.status_code} on {path}; sleeping {wait}s")
            time.sleep(wait)
            continue
        raise RuntimeError(f"FEC API {r.status_code} on {path}: {r.text[:200]}")
    raise RuntimeError(f"FEC API failed after retries on {path}")


def find_committee(query):
    """Helper for the console: look up committee IDs by name. Not used in the run."""
    data = fec_get("/committees/", q=query, per_page=20)
    for c in data.get("results", []):
        print(f"{c['committee_id']}  {c['name']}  ({c.get('committee_type_full', '?')})")


def get_recent_efilings(committee_id):
    """
    Real-time e-filings for a committee (covers ~last 4 months), newest first.
    Returns the raw records; we key on 'file_number' to detect new ones.
    """
    data = fec_get(
        "/efile/filings/",
        committee_id=committee_id,
        per_page=100,
        sort="-receipt_date",
    )
    return data.get("results", [])


def get_committee_totals(committee_id):
    """Processed cycle totals (nightly). Returns the most recent totals record."""
    data = fec_get(f"/committee/{committee_id}/totals/", cycle=CYCLE, per_page=1)
    results = data.get("results", [])
    return results[0] if results else {}


def get_realtime_ie_total(committee_id, days=120):
    """
    Sum independent-expenditure amounts from the REAL-TIME Schedule E e-file feed
    (~last 4 months). Returns (total_dollars, line_item_count).

    IMPORTANT — this is an UNOFFICIAL running estimate, not an authoritative figure.
    The e-file feed is raw: not normalized or coded by the FEC, so an amended report
    can repeat line items. We de-dupe best-effort on transaction_id to limit double
    counting, but the nightly `independent_expenditures` total stays authoritative.
    The point of this column is "what have they reported spending since the last
    processed total caught up" — a leading indicator, not a ledger.
    """
    min_date = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    seen = set()
    total = 0.0
    page = 1
    while page <= 50:  # safety cap: 50 pages x 100 = 5,000 line items
        data = fec_get(
            "/schedules/schedule_e/efile/",
            committee_id=committee_id,
            min_date=min_date,
            per_page=100,
            page=page,
        )
        results = data.get("results", [])
        if not results:
            break
        added = 0
        for rec in results:
            # Guard in case the committee filter is loose on the raw feed.
            cid = rec.get("committee_id") or rec.get("filer_committee_id_number")
            if cid and cid != committee_id:
                continue
            amt = rec.get("expenditure_amount")
            if amt is None:
                continue
            key = (
                rec.get("transaction_id")
                or f"{rec.get('file_number')}|{rec.get('line_number')}|{amt}"
            )
            if key in seen:
                continue
            seen.add(key)
            total += float(amt)
            added += 1
        # Stop if the page added nothing new (handles endpoints that ignore `page`).
        if added == 0:
            break
        pages = (data.get("pagination") or {}).get("pages")
        if pages and page >= pages:
            break
        page += 1
    return total, len(seen)


def get_electioneering_total(committee_id):
    """
    Sum electioneering-communication spending for a Form 9 filer (e.g. a 501(c)(4)
    that runs candidate-naming issue ads instead of express-advocacy IEs).

    Uses `calculated_candidate_share` — the FEC divides each disbursement by the
    number of candidates it names, so summing the shares reconstructs the total
    spend without double-counting multi-candidate ads. Returns (total, row_count).
    Caveat: like the IE feed, this isn't amendment-resolved, so treat as an estimate.
    """
    total = 0.0
    seen = set()  # also used to terminate if the endpoint ignores `page`
    page = 1
    while page <= 50:
        data = fec_get("/electioneering/", committee_id=committee_id,
                       cycle=CYCLE, per_page=100, page=page)
        results = data.get("results", [])
        if not results:
            break
        added = 0
        for rec in results:
            ident = f"{rec.get('sub_id')}|{rec.get('candidate_id')}"
            if ident in seen:
                continue
            share = rec.get("calculated_candidate_share")
            if share is None:
                continue
            seen.add(ident)
            total += float(share)
            added += 1
        if added == 0:
            break
        pages = (data.get("pagination") or {}).get("pages")
        if pages and page >= pages:
            break
        page += 1
    return total, len(seen)
    """Best available link to the actual filing document."""
    if rec.get("pdf_url"):
        return rec["pdf_url"]
    if rec.get("fec_url"):
        return rec["fec_url"]
    cid, fn = rec.get("committee_id"), rec.get("file_number")
    if cid and fn:
        return f"https://docquery.fec.gov/cgi-bin/forms/{cid}/{fn}/"
    return f"https://www.fec.gov/data/filings/?committee_id={cid}"


# --------------------------------------------------------------------------
# STATE (persists which filings we've already alerted on)
# --------------------------------------------------------------------------

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}  # { committee_id: [seen file_number, ...] }


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# --------------------------------------------------------------------------
# NOTIFICATIONS
# --------------------------------------------------------------------------

def notify_slack(text):
    if not SLACK_WEBHOOK_URL:
        return
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=15)
    except Exception as e:
        print(f"  [slack error] {e}")


def notify_email(subject, body):
    if not (SMTP_HOST and EMAIL_TO):
        return
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER or "fec-tracker@localhost"
    msg["To"] = EMAIL_TO
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            if SMTP_USER:
                s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(msg["From"], EMAIL_TO.split(","), msg.as_string())
    except Exception as e:
        print(f"  [email error] {e}")


def announce_new_filing(name, rec):
    form = rec.get("form_type", "?")
    received = rec.get("receipt_date", "?")
    link = filing_link(rec)
    label = {
        "F24": "24/48-hour IE report",
        "F3X": "periodic report (F3X)",
        "F5": "IE report (Form 5)",
    }.get(form, form)
    text = (
        f":rotating_light: *New FEC filing — {name}*\n"
        f"Type: {label}  |  Received: {received}\n"
        f"File #: {rec.get('file_number')}\n{link}"
    )
    print(f"  NEW: {name} {form} #{rec.get('file_number')} ({received})")
    notify_slack(text)
    notify_email(f"New FEC filing — {name} ({label})", text.replace("*", ""))


# --------------------------------------------------------------------------
# SPREADSHEET OUTPUT
# --------------------------------------------------------------------------

HEADERS = [
    "committee_id", "name", "cycle",
    "receipts (money raised)", "independent_expenditures (processed/nightly)",
    "realtime_IE_est (last ~4mo, unofficial)",
    "electioneering_comms_spend (processed)",
    "disbursements (total spending)", "cash_on_hand_end",
    "coverage_end_date", "last_updated_utc",
]

# Stable machine keys, same order as HEADERS / build_row — used for totals.json.
JSON_KEYS = [
    "committee_id", "name", "cycle",
    "receipts", "independent_expenditures", "realtime_ie_est",
    "electioneering_spend", "disbursements", "cash_on_hand_end",
    "coverage_end_date", "last_updated_utc",
]


def build_row(committee_id, name, totals, rt_total, ec_total):
    return [
        committee_id,
        name,
        CYCLE,
        totals.get("receipts"),
        totals.get("independent_expenditures"),
        round(rt_total, 2) if rt_total is not None else None,
        round(ec_total, 2) if ec_total is not None else None,
        totals.get("disbursements"),
        totals.get("last_cash_on_hand_end_period"),
        totals.get("coverage_end_date", ""),
        dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    ]


def write_google_sheet(rows):
    """Upsert one row per committee into a Google Sheet. Returns True if used."""
    if not (SHEET_ID and GOOGLE_SA_JSON):
        return False
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds = Credentials.from_service_account_info(
            json.loads(GOOGLE_SA_JSON),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet(WORKSHEET)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(WORKSHEET, rows=100, cols=len(HEADERS))

        existing = ws.get_all_values()
        if not existing:
            ws.update("A1", [HEADERS])
            existing = [HEADERS]

        # Map committee_id -> sheet row number (1-indexed, +1 for header)
        id_to_row = {r[0]: i + 1 for i, r in enumerate(existing) if r}
        for row in rows:
            cid = row[0]
            if cid in id_to_row:
                ws.update(f"A{id_to_row[cid]}", [row])
            else:
                ws.append_row(row, value_input_option="USER_ENTERED")
        print(f"  Wrote {len(rows)} rows to Google Sheet {SHEET_ID}")
        return True
    except Exception as e:
        print(f"  [sheets error] {e} — falling back to CSV")
        return False


def write_csv(rows):
    with CSV_FALLBACK.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADERS)
        w.writerows(rows)
    print(f"  Wrote {len(rows)} rows to {CSV_FALLBACK}")


def write_totals_json(rows):
    """
    Emit a clean, web-facing JSON file the tracker page can fetch directly.
    Includes per-committee numbers plus an aggregate headline figure.
    """
    records = [dict(zip(JSON_KEYS, r)) for r in rows]
    agg = {}
    for field in ("receipts", "independent_expenditures",
                  "realtime_ie_est", "electioneering_spend", "disbursements"):
        vals = [rec.get(field) for rec in records
                if isinstance(rec.get(field), (int, float))]
        agg[field] = round(sum(vals), 2) if vals else None
    payload = {
        "cycle": CYCLE,
        "last_updated_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "aggregate": agg,
        "committees": records,
    }
    TOTALS_JSON.write_text(json.dumps(payload, indent=2))
    print(f"  Wrote {TOTALS_JSON} ({len(records)} committees)")


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------

def main():
    if not COMMITTEES or all(cid.startswith("C00xxx") for cid in COMMITTEES):
        sys.exit("Set COMMITTEES (real committee IDs) before running. "
                 "Tip: python fec_tracker.py find \"committee name\"")

    state = load_state()
    rows = []

    for committee_id, name in COMMITTEES.items():
        print(f"Checking {name} ({committee_id})")
        seen = set(state.get(committee_id, []))

        # 1) detect + announce new filings (real-time feed)
        try:
            filings = get_recent_efilings(committee_id)
        except Exception as e:
            print(f"  [efile error] {e}")
            filings = []

        new_seen = set(seen)
        # On the very first run we record current filings WITHOUT alerting,
        # so you don't get spammed by months of backlog.
        first_run = committee_id not in state
        for rec in filings:
            fn = rec.get("file_number")
            if fn is None or fn in seen:
                continue
            if not first_run:
                announce_new_filing(name, rec)
            new_seen.add(fn)
        state[committee_id] = sorted(new_seen)
        if first_run:
            print(f"  First run: recorded {len(new_seen)} existing filings (no alerts)")

        # 2) pull spending for the spreadsheet — branch by filer type
        if committee_id in EC_FILERS:
            # Electioneering-communication filer: no F3X totals, no Schedule E.
            totals, rt_total = {}, None
            try:
                ec_total, ec_count = get_electioneering_total(committee_id)
                print(f"  Electioneering spend: ${ec_total:,.0f} "
                      f"across {ec_count} candidate-shares")
            except Exception as e:
                print(f"  [electioneering error] {e}")
                ec_total = None
        else:
            ec_total = None
            try:
                totals = get_committee_totals(committee_id)
            except Exception as e:
                print(f"  [totals error] {e}")
                totals = {}
            try:
                rt_total, rt_count = get_realtime_ie_total(committee_id)
                print(f"  Real-time IE est: ${rt_total:,.0f} "
                      f"across {rt_count} line items (last ~4mo)")
            except Exception as e:
                print(f"  [realtime IE error] {e}")
                rt_total = None
        rows.append(build_row(committee_id, name, totals, rt_total, ec_total))

    # 3) write spreadsheet (Sheets, else CSV) + web-facing JSON
    if rows and not write_google_sheet(rows):
        write_csv(rows)
    if rows:
        write_totals_json(rows)

    save_state(state)
    print("Done.")


if __name__ == "__main__":
    # Console helper:  python fec_tracker.py find "leading the future"
    if len(sys.argv) >= 3 and sys.argv[1] == "find":
        find_committee(sys.argv[2])
    else:
        main()
