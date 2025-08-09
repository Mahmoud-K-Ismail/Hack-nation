## Hackathon Orchestrator – Activity Log, Current Functionality, and Setup Guide

### What was implemented
- Backend service (`server.py`)
  - SSE stream for live logs and candidate/status updates: `GET /stream`
  - Health check: `GET /health`
  - Demo flow endpoints (no external creds required):
    - `GET /demo/run-topic?topic=...` reads `contacts.csv`, filters by expertise, emits candidates, and simulates outreach (Contacted → Accepted for first candidate), then emits `done`
    - `POST /demo/start-outreach` starts only the outreach simulation on already loaded candidates
  - Candidate tracking in-memory store with endpoints:
    - `POST /candidates/load` (load/update candidates and emit to SSE)
    - `GET /candidates` (list)
    - `PATCH /candidates/{email}/status` (update status; also emitted over SSE)

- Frontend (`index.html`)
  - API base is selectable via `?api=PORT` (default 8001)
  - CSV upload button to preload candidates
  - Dashboard auto-updates via SSE; pipeline shows Sourced/Contacted/Accepted
  - Launch button calls the new demo endpoint; the app sources from `contacts.csv` and simulates outreach end-to-end

- Orchestrator core (`main.py`)
  - Added optional callbacks (logs, candidates, candidate status) to support streaming when not in demo mode

- Communication tools (`tools/communication_tools.py`)
  - OAuth console fallback for headless
  - Defensive stub for `BaseTool` to avoid hard dependency during API-only demo

- Other
  - `requirements.txt` includes FastAPI + Uvicorn
  - `contacts.csv` added at project root (demo sourcing data)

### How the application functions now (demo mode)
1) UI loads and connects to SSE when you click Launch
2) Backend reads `contacts.csv`, filters by topic (case-insensitive match on the `expertise` column); if no matches, it uses all rows
3) Backend emits the filtered candidates and simulates outreach:
   - Marks everyone Contacted with log entries
   - Marks the first candidate Accepted and logs meeting creation step (simulated)
4) UI KPIs and pipeline statuses update live until a final `done` signal

### Setup – local demo (no external credentials)
Prereqs: Python 3.10+

1) Create venv and install packages
   ```bash
cd /Users/omarshehab/Desktop/Hack-nation/HackathonOrchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
# If needed explicitly: pip install fastapi uvicorn python-dotenv google-api-python-client google-auth-oauthlib google-auth-httplib2
   ```

2) Start backend API (port 8001)
   ```bash
uvicorn server:app --reload --port 8001
   ```

3) Serve the frontend (port 8080)
   ```bash
python -m http.server 8080
   ```

4) Open the UI in a browser
   - `http://127.0.0.1:8080/index.html?api=8001`

5) Demo flow
   - Ensure `contacts.csv` exists at the project root
   - Type a topic like "AI in FinTech" and click "Launch Sourcing Agent"
   - Watch logs stream and pipeline update (Sourced → Contacted → Accepted)

### Optional – real outreach (requires credentials)
- Set `.env`: `OPENAI_API_KEY=...`, `DUMMY_RUN=0`, and keep `credentials.json` in the project root
- Use outreach endpoints (`/outreach/run-flow`, etc.). First Gmail/Calendar action will prompt OAuth and create token files

### Testing checklist (for a teammate)
- API up: `curl -s http://127.0.0.1:8001/health` → `{ "ok": true }`
- SSE reachable: open `http://127.0.0.1:8001/stream` (keeps loading)
- Candidate load: `curl -s -X POST http://127.0.0.1:8001/candidates/load -H 'Content-Type: application/json' -d '{"candidates":[{"name":"Test","email":"test@example.org"}]}'`
- UI end-to-end: open `index.html?api=8001`, enter topic, click Launch, see logs and live status changes

### Troubleshooting
- 501 errors: you’re hitting the static server instead of the API. Use `http://127.0.0.1:8001` for API, `:8080` for the static site
- Port already in use: stop running instances (`pkill -f 'uvicorn server:app'`) or choose another port (`--port 8002`) and open the UI with `?api=8002`
- No logs/updates: refresh the page; verify `/stream` shows 200 OK in server logs

### Notes
- The demo flow avoids external dependencies and focuses on showing the business outcome and orchestration UI
- Replace `contacts.csv` with your own list to tailor the demo; the UI upload also works if you’d rather not restart


