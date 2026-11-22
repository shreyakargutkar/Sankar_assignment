# AutoReach AI — Influencer Research, Outreach & Reply Automation

An enterprise-ready, modular AI automation platform for researching Instagram influencers, analyzing campaign suitability with Claude AI, preventing duplicate leads, managing outreach pipeline stages, syncing records to Google Sheets, and running **approval-gated Gmail outreach with automated follow-ups**.

---

## 🌟 Key Features Implemented in Phase 1

1. **Influencer Research & Discovery Module**:
   - Campaign criteria input: Brand Name, Campaign Description, Influencer Niche, Target Location, Min & Max Follower count, Relevant Keywords.
   - Authorized & public creator discovery engine adhering strictly to Instagram terms (no scraping of private accounts or unauthorized botting).
   - Instant discovery batching with automatic initial lead status assignment.

2. **Deduplication Engine**:
   - Automatic normalization of Instagram usernames (`@` removal, casing, trimming) and profile URLs.
   - Dual-tier prevention: database uniqueness constraints + service layer duplicate detection with detailed import reporting (new leads vs skipped duplicates).

3. **Claude AI Intelligence Integration**:
   - Evaluates creator alignment against specific brand campaigns and target keywords.
   - Calculates an objective **Suitability Score out of 100**.
   - Categorizes influencers (e.g., Nano, Micro, Mid-Tier Creator, and niche specializations).
   - Generates detailed, actionable **Profile Summaries**.
   - Produces customized **Campaign Fit Explanations** highlighting why the creator matches the brand's outreach goals.
   - **Intelligent Demo Mode / Fallback**: Full end-to-end AI simulation when `ANTHROPIC_API_KEY` is not provided or `DEMO_MODE=True`, so the system functions without failing.

4. **Google Sheets API Integration**:
   - Cloud synchronization with Google Sheets API (`gspread` / Google Service Account).
   - Dual-mode architecture: seamlessly connects to Google Drive when credentials are provided, or automatically syncs to a local structured archive (`backend/app/data/google_sheets_synced_export.csv`) in demo mode.

5. **Multi-Source Data Ingestion**:
   - Public curated creator engine with dynamic keyword-matching creator synthesis.
   - CSV File Upload with smart header auto-mapping (handles columns like `name`, `username`, `profile_url`, `niche`, `followers`, `email`, `location`).
   - Downloadable CSV sample template.
   - Single lead manual entry modal.

6. **Outreach Lead Pipeline & Status Tracking**:
   - Full lifecycle status management:
     - `New Lead`
     - `Email Available`
     - `Email Sent`
     - `Follow-up Due`
     - `Replied`
     - `Interested`
     - `Not Interested`
     - `Collaboration Confirmed`
   - Interactive status dropdown badges with pipeline metrics filter.

7. **Professional High-Performance Dashboard**:
   - Built with React, Vite, and Tailwind CSS.
   - Real-time search by creator name, `@username`, niche, location, and email.
   - Filtering by Lead Status, Niche, Min Claude AI Score (80%+, 70%+, 55%+).
   - Column sorting (by Claude AI Score, Followers, Date Added, Name).
   - Dual view modes: Data Table and Grid Cards.
   - Multi-select batch operations (Batch Claude AI Analysis, Batch Google Sheets Sync, CSV Export).
   - Creator inspection drawer with copyable public business emails.

---

## 📬 Phase 2 — AI-Powered Gmail Outreach & Follow-ups

1. **Gmail API with OAuth 2.0**: Connect a mailbox via Google OAuth using one-time, expiring CSRF state. OAuth tokens are encrypted at rest with a Fernet key from the environment. Expired/revoked tokens surface a reconnect state instead of failing silently.
2. **Claude-personalized cold emails**: Each draft introduces the brand, explains the collaboration, states why the creator was selected, includes a CTA, identifies the sender, and adds an opt-out link.
3. **Preview workspace**: View, edit subject/body, approve or reject, then send only approved mail.
4. **Mandatory human approval** for the first send **and** every follow-up. The scheduler only queues drafts; it never sends on its own.
5. **Campaign tracking**: Email Sent, Follow-up Due, Replied, Interested, Not Interested (plus opt-out).
6. **Follow-up cadence**: First follow-up 3–5 days after the initial send; second 5–7 days after the first follow-up. Stops on reply, decline, or opt-out.
7. **History & timestamps**: `outreach_events` plus sent/approved timestamps on every email.
8. **Anti-spam**: Configurable daily cap (`DAILY_SEND_LIMIT`), spacing between sends, atomic send reservations, unique recipient claims for initial email, duplicate-sequence blocking, and opted-out/contacted address checks.
9. **Sheets sync after send**: The influencer row is upserted by database ID in the live Google Sheet or local CSV archive, including latest campaign, email subject, status, and sent timestamp.
10. **Simulated Gmail** when OAuth is not connected. UI and API clearly label `simulated` vs `live_gmail`. Simulated sends are archived to `backend/app/data/simulated_gmail_outbox.jsonl`.

---

## 💬 Phase 3 — Reply Management & Complete Workflow

1. **Inbox monitoring**: The APScheduler job polls Gmail every two minutes using the connected OAuth mailbox. It matches messages to sent influencer email addresses and their send time/thread, and uniquely records Gmail message IDs to prevent duplicate processing.
2. **Reply classification and CRM status**: Claude classifies replies as Interested, Not Interested, Pricing Enquiry, Collaboration Request, General Query, or Opt-out. Demo mode uses deterministic local rules. A detected reply first stops pending follow-ups and is persisted; if AI processing fails, the received message remains in history with a visible error and can be manually drafted.
3. **Contextual reply drafts**: Claude uses the campaign, original outreach and influencer response to prepare a contextual reply. The demo generator works without keys. Opt-outs are globally suppressed and never receive a reply draft.
4. **Human review is mandatory**: Reply drafts can be edited, approved or rejected in the Replies tab. Editing an approved draft revokes approval. Sending is restricted to approved replies and uses the original Gmail thread when available.
5. **Conversation history**: Each influencer has a chronological record of sent outreach, received replies and approved replies sent, with timestamps and live/simulated send mode.
6. **Sheets and CRM synchronization**: Classification updates the CRM status and upserts latest outreach/reply fields in Google Sheets, or in the local CSV archive when Sheets credentials are unavailable.
7. **Campaign analytics**: Shows researched and qualified influencers (score >= 70), sent mail, replies, interest/decline counts, collaboration confirmations and reply rate. Delivered count is explicitly unavailable unless Gmail supplies delivery information; API send success is not treated as a delivery receipt.
8. **Functional demo mode**: Add a demo reply to any sent message from the Replies tab, exercise classification, follow-up cancellation, human approval and simulated reply sending without contacting anyone.

### End-to-end workflow

`Instagram Research → Contact Collection → AI Filtering → Google Sheets → Personalized Gmail Outreach → Human Approval → Follow-up Drafts → Gmail Reply Detection → AI Classification/Draft → Human Approval → CRM/Sheets Update`

The discovery module uses public/curated sample records and manual/CSV contact collection; it does not scrape private Instagram accounts. Follow-up drafts are scheduled but never auto-sent. Initial outreach and every AI reply also require explicit approval.

## 🏗️ Project Architecture

```
sankar_assignment/
├── .env.example                       # Environment configuration template
├── .env                               # Active local environment variables
├── README.md                          # Documentation & execution guide
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── dependencies.py        # Database dependency injection
│   │   │   └── routes/
│   │   │       ├── discovery.py       # Research & CSV upload endpoints
│   │   │       ├── influencers.py     # CRUD & batch AI endpoints
│   │   │       ├── sheets.py          # Google Sheets sync endpoints
│   │   │       ├── gmail.py           # Gmail OAuth connect / callback
│   │   │       └── outreach.py        # Campaigns, approvals, replies, analytics
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic v2 settings loader
│   │   │   ├── database.py            # SQLite / SQLAlchemy connection
│   │   │   └── logging.py             # Structured application logger
│   │   ├── data/
│   │   │   ├── sample_influencers.csv # Pre-formatted sample CSV
│   │   │   └── google_sheets_synced_export.csv
│   │   ├── models/
│   │   │   ├── influencer.py          # SQLAlchemy ORM models & Enum
│   │   │   └── outreach.py            # Campaigns, email/reply history, Gmail tokens
│   │   ├── schemas/
│   │   │   ├── influencer.py          # Pydantic validation schemas
│   │   │   └── outreach.py
│   │   ├── services/
│   │   │   ├── ai_analyzer.py         # Claude AI API & intelligent simulator
│   │   │   ├── discovery_service.py   # Public creator & CSV parser
│   │   │   ├── google_sheets.py       # Google Sheets sync service
│   │   │   ├── influencer_service.py  # Business logic & deduplication
│   │   │   ├── email_generator.py     # Claude / simulated personalized emails
│   │   │   ├── reply_manager.py       # Reply classification & contextual drafts
│   │   │   ├── gmail_service.py       # OAuth + Gmail send / inbox poll
│   │   │   ├── outreach_service.py    # Outreach, reply review, CRM, analytics
│   │   │   └── followup_scheduler.py  # APScheduler background jobs
│   │   └── main.py                    # FastAPI application instance & lifespan
│   ├── requirements.txt               # Backend dependencies
│   └── tests/
│       ├── conftest.py
│       ├── test_influencer_api.py
│       ├── test_outreach_api.py
│       └── test_reply_management.py
└── frontend/
    ├── src/
    │   ├── components/                # Modular UI components
    │   │   ├── AddInfluencerModal.jsx
    │   │   ├── CampaignDiscoveryModal.jsx
    │   │   ├── CSVUploadModal.jsx
    │   │   ├── GoogleSheetsModal.jsx
    │   │   ├── InfluencerCard.jsx
    │   │   ├── InfluencerDetailModal.jsx
    │   │   ├── InfluencerTable.jsx
    │   │   ├── Navbar.jsx
    │   │   ├── StatsOverview.jsx
    │   │   └── StatusBadge.jsx
    │   ├── services/
    │   │   └── api.js                 # Frontend REST API client
    │   ├── utils/
    │   │   └── helpers.js             # Formatter & status helpers
    │   ├── App.jsx                    # Master dashboard coordinator
    │   ├── index.css                  # Tailwind styles
    │   └── main.jsx
    ├── index.html
    ├── package.json
    ├── tailwind.config.js
    └── vite.config.js
```

---

## 🚀 Quickstart & Startup Commands

### Prerequisites
- Python 3.10+ (tested with Python 3.13)
- Node.js 18+ and npm

---

### Step 1: Backend Setup & Execution

Open a terminal in the root directory `sankar_assignment`:

```bash
cd backend

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (already pre-installed in workspace)
pip install -r requirements.txt

# Run automated tests
PYTHONPATH=. pytest tests/ -v

# Start FastAPI backend server (Runs on port 8000)
uvicorn app.main:app --reload --port 8000
```

The backend interactive OpenAPI documentation will be accessible at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

### Step 2: Frontend Setup & Execution

Open a second terminal in `sankar_assignment`:

```bash
cd frontend

# Install dependencies (already pre-installed in workspace)
npm install

# Start Vite React development server (Runs on port 5173)
npm run dev
```

Open your browser at:
👉 **[http://localhost:5173](http://localhost:5173)**

---

## ⚙️ Configuration & Environment Variables

Configuration is loaded from `.env` in the root and `backend/` directory:

| Variable | Description | Default |
|---|---|---|
| `DEMO_MODE` | Set `True` to run with full realistic AI heuristics and local sheet sync without API keys | `True` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key (`sk-ant-...`) | `""` |
| `CLAUDE_MODEL` | Claude model identifier | `claude-3-5-sonnet-20241022` |
| `GOOGLE_SHEETS_CREDENTIALS_FILE` | Path to Google Service Account JSON | `google_credentials.json` |
| `GOOGLE_SPREADSHEET_ID` | Target Google Spreadsheet ID | `""` |
| `DATABASE_URL` | SQLite database URI | `sqlite:///./influencers.db` |
| `GMAIL_CLIENT_ID` | Google OAuth client ID | `""` |
| `GMAIL_CLIENT_SECRET` | Google OAuth client secret | `""` |
| `GMAIL_TOKEN_ENCRYPTION_KEY` | Fernet key used to encrypt OAuth tokens at rest; generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | `""` |
| `GMAIL_REDIRECT_URI` | Must match the Cloud Console redirect | `http://127.0.0.1:8000/api/v1/gmail/callback` |
| `DAILY_SEND_LIMIT` | Max sends per calendar day (live + simulated) | `40` |
| `MIN_SECONDS_BETWEEN_SENDS` | Pause between messages | `0.25` |
| `FOLLOWUP_1_MIN_DAYS` / `FOLLOWUP_1_MAX_DAYS` | First follow-up window | `3` / `5` |
| `FOLLOWUP_2_MIN_DAYS` / `FOLLOWUP_2_MAX_DAYS` | Second follow-up window | `5` / `7` |

### Using Live APIs:
1. **Claude AI**: Paste your Anthropic API key into `.env` (`ANTHROPIC_API_KEY=sk-ant-...`) and set `DEMO_MODE=False`.
2. **Google Sheets**: Download your Google Cloud Service Account JSON key, save it as `backend/google_credentials.json`, share your Google Spreadsheet with the service account email, and set `GOOGLE_SPREADSHEET_ID=<your_sheet_id>`.

---

## 🧪 Testing

Execute the test suite to verify end-to-end functionality:

```bash
cd backend
source venv/bin/activate
PYTHONPATH=. pytest tests/ -v

cd ../frontend
npm run build
```

The automated tests cover Phase 1 research/sync, Phase 2 outreach, and Phase 3:
- Approval is required before send
- Editing an approved draft revokes its approval
- Duplicate sequences are blocked
- Follow-ups are drafted (not auto-sent) and stop after a reply
- Declines stop follow-ups without creating a global opt-out
- Opt-out cancels remaining mail
- Daily send caps are enforced for simulated and live sends
- Gmail OAuth tokens are encrypted at rest and callbacks reject unissued state
- Sheets sync upserts rather than creating duplicate rows
- Gmail stays in simulated mode without OAuth credentials
- All six reply classifications, duplicate Gmail message handling and opt-out suppression
- Follow-up cancellation on received replies, approval/edit invalidation and simulated reply sending
- Conversation history, campaign analytics and Google Sheets reply metadata

---

## 🔐 How to configure integrations and demonstrate all phases

You can run the complete workflow **without** Gmail, Claude or Sheets credentials. The UI labels Gmail as **SIMULATED GMAIL**, reply classification/generation as demo behavior, and Sheets uses a local CSV archive. Simulated messages are written to `backend/app/data/simulated_gmail_outbox.jsonl` and never leave the machine.

### Run the app

```bash
# Terminal 1
cd backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The backend seeds sample creators when the database is empty. Select creators with email addresses and open **Outreach**.

Workflow:
1. Generate AI drafts (Claude live if `DEMO_MODE=False` and `ANTHROPIC_API_KEY` is set; otherwise simulated Claude).
2. Edit subject/body in the preview pane.
3. **Approve** or **Reject**. Nothing sends until Approve + **Send approved**.
4. After send, lead status becomes **Email Sent**. A follow-up due date is stored (3–5 days).
5. The background scheduler (every 2 minutes) creates **follow-up drafts** when due. Approve those before they can send.
6. In **Replies**, click **Check Gmail inbox** for live Gmail or select a sent email and add a demo reply. Verify classification and that all pending follow-ups are cancelled.
7. Edit the contextual reply draft, approve it and click **Send approved replies**. The UI/API reports whether sending was live or simulated.
8. Review chronological conversation history and the **Analytics** tab; verify CRM status and Google Sheets (or the local CSV archive) metadata.
9. To test opt-out, add a reply such as “Please unsubscribe me and stop emailing me.” No response draft is generated and future outreach is suppressed.

Demo shortcut: **Demo: generate due follow-up drafts now** forces the 3–7 day wait so you can test follow-ups immediately.

### Connect a real Gmail mailbox

1. In [Google Cloud Console](https://console.cloud.google.com/) create (or pick) a project.
2. Enable the **Gmail API**.
3. Configure the OAuth consent screen (External is fine for testing). Add your Google account as a test user.
4. Create **OAuth client ID** type **Web application**.
5. Add authorized redirect URI exactly:
   `http://127.0.0.1:8000/api/v1/gmail/callback`
6. Copy the client ID and secret into `backend/.env` (the configuration file used by the documented backend command):

```bash
GMAIL_CLIENT_ID=xxxxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=xxxxx
GMAIL_TOKEN_ENCRYPTION_KEY=<generated-fernet-key>
GMAIL_REDIRECT_URI=http://127.0.0.1:8000/api/v1/gmail/callback
FRONTEND_URL=http://localhost:5173
DEMO_MODE=False
ANTHROPIC_API_KEY=sk-ant-...   # optional; otherwise email copy is simulated
```

7. Generate a Fernet key using the command in the configuration table. Put it in `GMAIL_TOKEN_ENCRYPTION_KEY` in `backend/.env`; keep the same key permanently and do not commit it.
8. Restart the backend. In the Outreach workspace click **Connect Gmail OAuth**, sign in, and grant `gmail.send` + `gmail.readonly`.
9. The badge switches to **LIVE GMAIL**. Approved sends go through the Gmail API. The inbox monitor polls every two minutes. Failures (including expired refresh tokens) are logged and surfaced; they are **not** silently converted to simulated sends. OAuth tokens are unreadable without the same encryption key.

Scopes used: `gmail.send` and `gmail.readonly`.

### Configure Claude and Google Sheets

- For live classification and copy generation, set a valid `ANTHROPIC_API_KEY` and `DEMO_MODE=False` in `backend/.env`. Without a valid key, the app uses its clearly labeled local demo classifier/drafter.
- For live Sheets sync, create a Google service account, enable Google Sheets API, place its JSON key in the configured `GOOGLE_SHEETS_CREDENTIALS_FILE`, share the target spreadsheet with the service-account email, and set `GOOGLE_SPREADSHEET_ID`. Without these credentials, sync is written to the local CSV archive. Gmail OAuth is configured separately.

### Safeguards worth knowing

- Daily cap applies to both live and simulated sends.
- The same influencer + sequence cannot be sent twice.
- Follow-ups are never auto-sent; only auto-drafted for approval.
- Opt-out URL format: `http://127.0.0.1:8000/api/v1/outreach/opt-out/<token>`
