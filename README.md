# CivicPulse

An iPhone app + backend for civic engagement around AI policy: readers get a
curated feed of news articles, read them inline, and are then guided into
action — messaging their member of Congress (with an AI-drafted letter built
around their own thoughts), registering to vote, or supporting pro-AI-safety
candidates. A web admin dashboard handles curation, push notifications, and
analytics.

```
CivicPulse/
├── backend/   FastAPI server + SQLite + admin dashboard (Python 3.11+)
└── ios/       SwiftUI iPhone app (iOS 17+, generated with XcodeGen)
```

## Feature map

| Requirement | Where it lives |
|---|---|
| Find your rep + senators by zip, with contact info | `GET /api/reps/lookup?zip=` → onboarding + **My Reps** tab |
| Live curated news feed | Admin dashboard "Articles" tab → **Feed** tab in app |
| Admin push notifications with brief thoughts | Admin "Send a push" → APNs alert on devices |
| Read the article inline | `ArticleDetailView` (in-app WKWebView) |
| Message your office: your thoughts over an AI summary | `POST /api/messages/draft` (Claude) → compose flow → call / copy / contact-form delivery |
| Get a message back from the office | Admin logs the office reply → user gets a push + sees it in **Inbox** |
| Engagement dashboard | Admin "Engagement" tab (views / reads / shares / actions / messages per article) |
| Congressional-contact dashboard | Admin "Congressional Contacts" tab (per-office counts, full message text, reply logging) |
| Register to vote / support candidates | **Actions** tab (vote.gov links + admin-curated candidate list) |

## Backend — quick start

```bash
cd CivicPulse/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set ADMIN_TOKEN at minimum
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Admin dashboard: http://localhost:8000/admin (enter your `ADMIN_TOKEN` top right)

On first start the server downloads two public-domain datasets and caches them
in `backend/data/`:

- `legislators-current.json` (the @unitedstates project) — every sitting
  member with phone, contact form, office address, photo.
- `zccd.csv` (OpenSourceActivismTech) — zip → congressional district. Note a
  zip can span multiple districts; the API returns every matching House member
  and the app lets the user pick.

Without network access it falls back to a tiny bundled sample so the demo
still works end-to-end.

### Optional integrations

| Env var | Enables |
|---|---|
| `ANTHROPIC_API_KEY` | AI article summaries + AI-drafted constituent letters (Claude). Without it, clean text templates are used. |
| `APNS_TEAM_ID` / `APNS_KEY_ID` / `APNS_KEY_PATH` / `APNS_TOPIC` | Real push notifications. Without them, pushes are logged but not delivered. |

### How "message your office" works

Congressional offices don't accept email from arbitrary senders — they use
phone lines and webforms (the official CWC API is restricted to approved
vendors). So the app:

1. Drafts the letter server-side: a boilerplate intro + AI summary of the
   article, with the constituent's own thoughts kept central
   (`POST /api/messages/draft`).
2. Logs the final message (`POST /api/messages`) so it appears on the admin
   contacts dashboard.
3. Hands the user the actual delivery channel: tap-to-call the office, copy
   the text, or open the office's official contact form pre-informed.
4. When the office responds (email/phone to the constituent, or to your org),
   an admin logs the reply on the dashboard — the user gets a push and sees it
   in the app's Inbox.

## iOS app — quick start

```bash
cd CivicPulse/ios
brew install xcodegen          # once
xcodegen generate
open CivicPulse.xcodeproj
```

Set the backend URL in `CivicPulse/Config.swift` (defaults to
`http://localhost:8000` for the simulator). See `ios/README.md` for push
notification setup (APNs key, bundle id, entitlements).

## Admin workflow

1. Open `/admin`, paste your admin token.
2. **Curate**: add an article (title, URL, source, optional image/tags). Leave
   the summary blank and paste the article text to have Claude write the
   summary. Add "your note to readers" — it shows highlighted in the feed.
3. **Notify**: pick the article, write your brief thoughts, send the push.
4. **Watch engagement**: views → reads → action-opens → messages, per article.
5. **Track contacts**: see which offices are being contacted most, read what
   constituents are sending, and log office replies (which notifies the user).
