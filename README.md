# FEC Super PAC IE Tracker

Polls the FEC for new independent-expenditure filings by a fixed set of super PACs,
alerts you (Slack/email), and snapshots money-raised + spending totals to a spreadsheet.

## Why API, not scraping
The FEC's OpenFEC API is the source the public website is built on. Scraping the
HTML is slower, more fragile, and gives you nothing extra — the processed data is
updated nightly either way. We use these endpoints:

- `/efile/filings/` — **real-time** feed of electronic filings → drives ALERTS.
  (Covers only ~the last 4 months, which is fine for "what just got filed.")
- `/committee/{id}/totals/` — **processed nightly** totals → drives the SPREADSHEET
  (`receipts` = money raised, `independent_expenditures` + `disbursements` = spending).
- `/schedules/schedule_e/efile/` — **real-time** itemized IEs (~last 4 months) → summed
  into the `realtime_IE_est` column. An **unofficial leading indicator**: the raw feed
  isn't normalized or de-duplicated by the FEC, so amendments can overlap. The script
  de-dupes best-effort, but the nightly `independent_expenditures` figure stays
  authoritative. Use this column to see spend that hasn't hit processed totals yet.
- `/electioneering/` — processed electioneering-communication spending, for filers
  listed in `EC_FILERS` (e.g. Public First Action Inc., C30003586). These 501(c)(4)
  filers report candidate-naming issue ads on Form 9 instead of Schedule E IEs, so
  their spend lands in the `electioneering_comms_spend` column and their `receipts`
  stay blank (they don't itemize donors to the FEC). New-filing alerts still work
  normally. "Build American AI" has no FEC registration at all and can't be tracked.

## Setup (≈15 min)

1. **Get a free FEC API key:** https://api.open.fec.gov/developers/
2. **Find your committee IDs.** Either browse https://www.fec.gov/data/committees/
   or run locally:
   ```bash
   pip install requests
   FEC_API_KEY=yourkey python fec_tracker.py find "leading the future"
   ```
   Put the results in the `FEC_COMMITTEES` secret as JSON:
   `{"C00916114":"Leading the Future","C30003586":"Public First Action Inc."}`
   (If you override `FEC_COMMITTEES`, also set `EC_FILERS` in code for any
   electioneering-communication filers like C30003586.)
3. **Notifications — pick one or both:**
   - *Slack:* create an Incoming Webhook, set `SLACK_WEBHOOK_URL`.
   - *Email:* set `SMTP_HOST/PORT/USER/PASS` and `EMAIL_TO`.
4. **Spreadsheet (Google Sheets, recommended):**
   - Create a Google Cloud service account, enable the Sheets API, download its
     JSON key. Paste the whole JSON into the `GOOGLE_SERVICE_ACCOUNT_JSON` secret.
   - Create a Sheet, share it with the service account's email (Editor), and set
     `SHEET_ID` to the long id in the Sheet URL.
   - No Sheets config? It writes `super_pac_totals.csv` instead.
5. **Schedule it.** Push this folder to a GitHub repo and add the secrets under
   *Settings → Secrets and variables → Actions*. The workflow runs every 30 min
   and commits its state file back so it remembers what it already saw.

## Local test run
```bash
pip install requests gspread google-auth
export FEC_API_KEY=yourkey
export FEC_COMMITTEES='{"C00876880":"Leading the Future"}'
python fec_tracker.py
```
First run records existing filings silently (no backlog spam); subsequent runs alert
only on genuinely new ones.

## Feeding your website tracker
Each run writes **`totals.json`** — a clean, web-ready file with one entry per
committee plus an `aggregate` block (summed receipts / IE / disbursements) for a
headline number. Shape:

```json
{
  "cycle": 2026,
  "last_updated_utc": "2026-06-05T17:57:08Z",
  "aggregate": { "receipts": 1500000, "independent_expenditures": 600000,
                 "realtime_ie_est": 770000, "disbursements": 900000 },
  "committees": [ { "committee_id": "C00...", "name": "...", "receipts": 1000000,
                    "independent_expenditures": 600000, "realtime_ie_est": 650000,
                    "disbursements": 700000, "cash_on_hand_end": 300000,
                    "coverage_end_date": "2026-03-31", "last_updated_utc": "..." } ]
}
```

The GitHub Action commits `totals.json` on every run. To consume it on the
`/ai-super-pac-tracker/` page, pick one:
- **Fetch the raw file** client-side from
  `https://raw.githubusercontent.com/<you>/<repo>/main/totals.json` (CORS-enabled;
  CDN-cached ~5 min).
- **GitHub Pages:** enable Pages on the repo for a clean stable URL.
- **Push to WordPress:** add a step that uploads `totals.json` to your WP Engine
  site (e.g. via SFTP or the REST API) so it's served from your own domain.

The Sheet/CSV remains the human-readable view; `totals.json` is the machine feed.
