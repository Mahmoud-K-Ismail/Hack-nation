import asyncio
import json
from typing import AsyncIterator, Callable, List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import sys
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from core.main import run_orchestrator
from services.speaker_finder_service import speaker_finder_service


load_dotenv()

app = FastAPI(title="Hackathon Orchestrator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EventBus:
    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active_run: bool = False

    async def emit(self, event: str, data: dict) -> None:
        await self.queue.put((event, data))

    async def sse(self) -> AsyncIterator[bytes]:
        try:
            while True:
                event, data = await self.queue.get()
                payload = f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")
                yield payload
        except asyncio.CancelledError:
            return


bus = EventBus()


class CandidateStore:
    """In-memory candidate store for tracking statuses across the flow."""
    def __init__(self) -> None:
        # email -> record
        self._store: dict[str, dict] = {}

    def load(self, candidates: list[dict]) -> list[dict]:
        for c in candidates:
            email = c.get("email")
            if not email:
                continue
            rec = self._store.get(email, {})
            rec.update({
                "name": c.get("name") or rec.get("name"),
                "email": email,
                "expertise": c.get("expertise") or rec.get("expertise", ""),
                "status": c.get("status") or rec.get("status", "Sourced"),
            })
            self._store[email] = rec
        return list(self._store.values())

    def all(self) -> list[dict]:
        return list(self._store.values())

    def update_status(self, email: str, status: str) -> dict | None:
        rec = self._store.get(email)
        if rec is None:
            return None
        rec["status"] = status
        return rec

    def set_ref(self, email: str, ref: str) -> None:
        if email in self._store:
            self._store[email]["refToken"] = ref


candidate_store = CandidateStore()


@app.post("/run")
async def start_run(topic: str) -> dict:
    if bus.active_run:
        raise HTTPException(status_code=409, detail="A run is already in progress")

    bus.active_run = True

    loop = asyncio.get_running_loop()

    def on_log(message: str) -> None:
        asyncio.run_coroutine_threadsafe(bus.emit("log", {"message": message}), loop)

    def on_candidates_found(cands: List[dict]) -> None:
        asyncio.run_coroutine_threadsafe(bus.emit("candidates", cands), loop)

    def on_candidate_status(index: int, status: str) -> None:
        asyncio.run_coroutine_threadsafe(
            bus.emit("candidate_status", {"index": index, "status": status}),
            loop,
        )

    async def run_in_thread() -> None:
        try:
            await loop.run_in_executor(
                None,
                lambda: run_orchestrator(
                    topic=topic,
                    on_log=on_log,
                    on_candidates_found=on_candidates_found,
                    on_candidate_status=on_candidate_status,
                    simulate_timing=True,
                ),
            )
        finally:
            await bus.emit("done", {"ok": True})
            bus.active_run = False

    asyncio.create_task(run_in_thread())
    return {"status": "started"}


@app.get("/stream")
async def stream_events() -> StreamingResponse:
    async def gen():
        async for chunk in bus.sse():
            yield chunk
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


# --- Demo helpers (no external APIs) ---
async def _simulate_outreach_sequence(enriched: List[dict], poll_interval: float = 0.8) -> None:
    """Simulate contacting each candidate and acceptance of the first one."""
    try:
        await bus.emit("log", {"message": "[SchedulingAgent] Initializing outreach sequence..."})
        # Contact each candidate
        for idx, e in enumerate(enriched):
            await asyncio.sleep(poll_interval)
            await bus.emit("log", {"message": f"[SchedulingAgent] Sending outreach email to {e['name']}."})
            candidate_store.update_status(e["email"], "Contacted")
            await bus.emit("candidate_status", {"email": e["email"], "status": "Contacted"})

        # Accept the first candidate
        if enriched:
            await asyncio.sleep(poll_interval + 0.4)
            first = enriched[0]
            await bus.emit("log", {"message": f"[SchedulingAgent] Received positive reply from {first['name']}. Scheduling meeting."})
            candidate_store.update_status(first["email"], "Accepted")
            await bus.emit("candidate_status", {"email": first["email"], "status": "Accepted"})

        await asyncio.sleep(0.4)
        await bus.emit("log", {"message": "[SchedulingAgent] Task complete."})
        await asyncio.sleep(0.2)
        await bus.emit("done", {"ok": True})
    except asyncio.CancelledError:
        return


def _read_contacts_csv() -> List[dict]:
    import csv, os
    path = os.path.join(os.path.dirname(__file__), "contacts.csv")
    if not os.path.exists(path):
        return []
    out: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("name") or "").strip()
            email = (row.get("email") or "").strip()
            expertise = (row.get("expertise") or "").strip()
            if email:
                out.append({"name": name, "email": email, "expertise": expertise, "status": "Sourced"})
    return out


@app.post("/demo/start-outreach")
async def demo_start_outreach() -> dict:
    enriched = candidate_store.all()
    if not enriched:
        await bus.emit("log", {"message": "[Outreach] No candidates loaded."})
        await bus.emit("done", {"ok": False})
        return {"ok": False, "reason": "no candidates"}
    asyncio.create_task(_simulate_outreach_sequence(enriched))
    return {"ok": True}


@app.get("/demo/run-topic")
async def demo_run_topic(topic: str) -> dict:
    """Load candidates from contacts.csv filtered by topic substr and simulate outreach."""
    all_contacts = _read_contacts_csv()
    if not all_contacts:
        await bus.emit("log", {"message": "[SourcingAgent] No contacts.csv found."})
        await bus.emit("done", {"ok": False})
        return {"ok": False, "reason": "no contacts.csv"}
    # Filter by topic present in expertise (case-insensitive)
    t = (topic or "").lower()
    filtered = [c for c in all_contacts if t in (c.get("expertise", "").lower())]
    if not filtered:
        filtered = all_contacts  # fallback to all if no match

    # Load into store and emit candidates
    candidate_store.load(filtered)
    await bus.emit("log", {"message": "[SourcingAgent] Found candidates from CSV."})
    await bus.emit("candidates", [
        {"name": r.get("name"), "email": r.get("email"), "expertise": r.get("expertise", ""), "status": r.get("status", "Sourced")}
        for r in candidate_store.all()
    ])

    # Simulate outreach
    asyncio.create_task(_simulate_outreach_sequence(filtered))
    return {"ok": True, "count": len(filtered)}


# --- New Individual Candidate Endpoints ---

@app.post("/outreach/send-individual")
async def send_individual_email(payload: dict = Body(...)) -> dict:
    """Send email to a single candidate with GPT-generated personalized content."""
    candidate = payload.get("candidate", {})
    subject = payload.get("subject", "Hackathon Invitation")
    body_template = payload.get("bodyTemplate", "Hi {name}, we'd love to invite you.")
    
    if not candidate.get("email"):
        raise HTTPException(status_code=400, detail="candidate email required")
    
    try:
        # Import OpenAI for content enhancement
        import openai
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Generate personalized email using GPT
        if openai.api_key:
            try:
                client = openai.OpenAI(api_key=openai.api_key)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at writing professional, personalized invitation emails for hackathon speakers and jury members. Make emails warm, specific to their expertise, and compelling."
                        },
                        {
                            "role": "user",
                            "content": f"""
                            Please enhance this email template for {candidate.get('name', 'there')} who has expertise in {candidate.get('expertise', 'technology')}:
                            
                            Template: {body_template}
                            
                            Make it more personalized and engaging while keeping it professional and concise.
                            """
                        }
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                enhanced_body = response.choices[0].message.content.strip()
            except Exception as e:
                print(f"GPT enhancement failed: {e}")
                enhanced_body = body_template.format(name=candidate.get('name', 'there'))
        else:
            enhanced_body = body_template.format(name=candidate.get('name', 'there'))
        
        # Generate reference token
        ref_token = f"{hash((candidate['email'], subject)) & 0xfffffff:x}"
        
        # For demo purposes, simulate email sending
        # In production, this would integrate with actual email service
        result = {
            "ok": True,
            "to": candidate["email"],
            "refToken": ref_token,
            "subject": subject,
            "body": enhanced_body,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # Update candidate store
        candidate_store.load([{
            "name": candidate.get("name"),
            "email": candidate["email"],
            "expertise": candidate.get("expertise", ""),
            "status": "Contacted"
        }])
        candidate_store.set_ref(candidate["email"], ref_token)
        
        await bus.emit("log", {"message": f"Enhanced email sent to {candidate.get('name', candidate['email'])}"})
        await bus.emit("candidate_status", {"email": candidate["email"], "status": "Contacted"})
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@app.post("/outreach/check-response")
async def check_individual_response(payload: dict = Body(...)) -> dict:
    """Check for response from a specific candidate and analyze it with GPT."""
    ref_token = payload.get("refToken")
    candidate_email = payload.get("candidateEmail")
    
    if not ref_token or not candidate_email:
        raise HTTPException(status_code=400, detail="refToken and candidateEmail required")
    
    try:
        # Simulate response checking (in production, this would check actual email)
        # For demo, we'll simulate responses for some candidates
        import random
        import time
        
        # Simulate response arrival based on time elapsed
        current_time = time.time()
        
        # Create a deterministic but seemingly random response pattern
        response_seed = hash(ref_token) % 100
        time_factor = int(current_time) % 60  # Change response over time
        
        # 30% chance of response after some time
        has_response = (response_seed + time_factor) % 100 < 30
        
        if not has_response:
            return {
                "ok": True,
                "hasResponse": False,
                "message": "No response yet"
            }
        
        # Generate simulated response
        simulated_responses = [
            {
                "text": "Hi! Yes, I'm very interested in participating. I'm available on Tuesday 2-4 PM, Wednesday 10 AM-12 PM, or Friday 3-5 PM next week.",
                "isPositive": True,
                "times": ["Tuesday 2-4 PM", "Wednesday 10 AM-12 PM", "Friday 3-5 PM"]
            },
            {
                "text": "Thanks for reaching out! I'd love to be involved. I can do Monday 1-3 PM, Thursday 9-11 AM, or next Friday afternoon.",
                "isPositive": True,
                "times": ["Monday 1-3 PM", "Thursday 9-11 AM", "Friday 2-4 PM"]
            },
            {
                "text": "Thank you for the invitation, but I'm not available during that time period. Good luck with your event!",
                "isPositive": False,
                "times": []
            },
            {
                "text": "Sounds interesting! I'm available most weekday afternoons. How about Wednesday 2 PM or Thursday 3 PM?",
                "isPositive": True,
                "times": ["Wednesday 2 PM", "Thursday 3 PM"]
            }
        ]
        
        response_data = random.choice(simulated_responses)
        
        # Use GPT to analyze response (if available)
        try:
            import openai
            import os
            
            openai.api_key = os.getenv("OPENAI_API_KEY")
            
            if openai.api_key:
                client = openai.OpenAI(api_key=openai.api_key)
                analysis = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI that analyzes email responses to speaker invitations. Extract whether the response is positive/negative and any available time slots mentioned."
                        },
                        {
                            "role": "user",
                            "content": f"""
                            Analyze this email response to a hackathon speaker invitation:
                            
                            "{response_data['text']}"
                            
                            Return a JSON with:
                            1. isPositive: boolean (true if they're interested)
                            2. availableTimes: array of time slots mentioned
                            3. sentiment: brief description
                            """
                        }
                    ],
                    max_tokens=200,
                    temperature=0.3
                )
                
                # Parse GPT response (simplified for demo)
                gpt_result = response_data  # Use simulated data as fallback
                
        except Exception as e:
            print(f"GPT analysis failed: {e}")
            # Use simulated data as fallback
        
        return {
            "ok": True,
            "hasResponse": True,
            "responseText": response_data["text"],
            "isPositive": response_data["isPositive"],
            "availableTimes": response_data["times"],
            "sentiment": "positive" if response_data["isPositive"] else "negative"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check response: {str(e)}")


@app.post("/outreach/schedule-meeting")
async def schedule_individual_meeting(payload: dict = Body(...)) -> dict:
    """Schedule a meeting with a candidate for a selected time slot."""
    candidate = payload.get("candidate", {})
    selected_time = payload.get("selectedTime")
    summary = payload.get("summary", "Hackathon Discussion")
    description = payload.get("description", "Meeting to discuss hackathon participation")
    duration = payload.get("duration", 30)
    
    if not candidate.get("email") or not selected_time:
        raise HTTPException(status_code=400, detail="candidate email and selectedTime required")
    
    try:
        # For demo purposes, simulate meeting creation
        # In production, this would integrate with Google Calendar API
        
        meeting_id = f"meet_{hash((candidate['email'], selected_time)) & 0xffffff:x}"
        meeting_link = f"https://meet.google.com/{meeting_id}"
        
        # Simulate calendar integration
        calendar_result = {
            "eventId": f"event_{meeting_id}",
            "meetingLink": meeting_link,
            "scheduledTime": selected_time,
            "summary": summary,
            "description": description,
            "attendees": [candidate["email"]]
        }
        
        # Update candidate status
        candidate_store.update_status(candidate["email"], "Scheduled")
        
        await bus.emit("log", {"message": f"Meeting scheduled with {candidate.get('name', candidate['email'])} for {selected_time}"})
        await bus.emit("candidate_status", {"email": candidate["email"], "status": "Scheduled"})
        
        return {
            "ok": True,
            "meetingLink": meeting_link,
            "eventId": calendar_result["eventId"],
            "scheduledTime": selected_time,
            "message": f"Meeting scheduled for {selected_time}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule meeting: {str(e)}")

# Run with: uvicorn server:app --reload


@app.post("/outreach/send")
async def send_outreach(payload: dict = Body(...)) -> dict:
    """Send outreach emails to a provided candidate list.

    payload example:
    {
      "subject": "Invitation to speak",
      "bodyTemplate": "Hi {name}, ...",
      "candidates": [{"name":"...","email":"..."}, ...]
    }
    """
    subject: str = payload.get("subject") or "Hackathon Invitation"
    body_template: str = payload.get("bodyTemplate") or "Hi {name}, we'd love to invite you."
    candidates: List[dict] = payload.get("candidates") or []
    if not candidates:
        raise HTTPException(status_code=400, detail="candidates required")

    # Lazy import to avoid requiring google libs unless endpoints are used
    from tools.communication_tools import CommunicationTools  # type: ignore

    results: List[dict] = []
    for c in candidates:
        name = c.get("name") or "there"
        email = c.get("email")
        if not email:
            continue
        ref = f"{hash((email, subject)) & 0xfffffff:x}"
        body = body_template.format(name=name)
        res = CommunicationTools.send_email(to=email, subject=subject, body=body, ref_token=ref)
        try:
            results.append(json.loads(res))
        except Exception:
            results.append({"ok": False, "to": email})
        # Track candidate and status
        candidate_store.load([{"name": name, "email": email, "status": "Contacted"}])
        candidate_store.set_ref(email, ref)
        await bus.emit("candidate_status", {"email": email, "status": "Contacted"})
    return {"ok": True, "sent": results}


@app.post("/outreach/check-replies")
async def check_replies(payload: dict = Body(...)) -> dict:
    """Check for replies using ref tokens returned from /outreach/send.

    payload example:
    { "refs": ["abc123", "def456"] }
    """
    from tools.communication_tools import CommunicationTools  # type: ignore
    refs: List[str] = payload.get("refs") or []
    found: dict = {}
    for ref in refs:
        msgs = CommunicationTools.search_replies_by_ref_token(ref)
        found[ref] = msgs
    return {"ok": True, "replies": found}


@app.post("/outreach/schedule-on-reply")
async def schedule_on_reply(payload: dict = Body(...)) -> dict:
    """Given candidates and their ref tokens, schedule meetings for those with replies."""
    candidates: List[dict] = payload.get("candidates") or []
    summary: str = payload.get("summary") or "Introductory Meeting"
    description: str = payload.get("description") or "Intro call"
    duration: int = int(payload.get("duration", 30))
    timezone_name: Optional[str] = payload.get("timezone")

    from tools.communication_tools import CommunicationTools  # type: ignore
    scheduled: List[dict] = []
    for c in candidates:
        email = c.get("email")
        ref = c.get("refToken")
        if not email or not ref:
            continue
        msgs = CommunicationTools.search_replies_by_ref_token(ref)
        if msgs:
            res = CommunicationTools.schedule_meeting(
                attendees=[email],
                summary=summary,
                description=description,
                duration_minutes=duration,
                timezone_name=timezone_name,
            )
            try:
                scheduled.append(json.loads(res))
            except Exception:
                scheduled.append({"eventId": None, "calendarLink": None, "meetLink": None})
            candidate_store.update_status(email, "Accepted")
            await bus.emit("candidate_status", {"email": email, "status": "Accepted"})
            await bus.emit("log", {"message": f"[Scheduling] Meeting created for {email}"})
    return {"ok": True, "scheduled": scheduled}


@app.post("/outreach/run-flow")
async def run_full_outreach_flow(payload: dict = Body(...)) -> dict:
    """Send to candidates, poll for replies, schedule meetings upon reply. Emits SSE events.

    payload example:
    {
      "subject": "Invitation to speak",
      "bodyTemplate": "Hi {name}, ...",
      "candidates": [{"name":"...","email":"..."}],
      "windowMinutes": 30,
      "pollEverySeconds": 20,
      "summary": "Introductory Meeting",
      "description": "Kickoff",
      "duration": 30,
      "timezone": "UTC"
    }
    """
    if bus.active_run:
        raise HTTPException(status_code=409, detail="A run is already in progress")

    bus.active_run = True
    loop = asyncio.get_running_loop()

    subject: str = payload.get("subject") or "Hackathon Invitation"
    body_template: str = payload.get("bodyTemplate") or "Hi {name}, we'd love to invite you."
    candidates: List[dict] = payload.get("candidates") or []
    window_minutes: int = int(payload.get("windowMinutes", 30))
    poll_interval: int = int(payload.get("pollEverySeconds", 20))
    summary: str = payload.get("summary") or "Introductory Meeting"
    description: str = payload.get("description") or "Intro call"
    duration: int = int(payload.get("duration", 30))
    tz: Optional[str] = payload.get("timezone")

    async def flow_task():
        try:
            await bus.emit("log", {"message": "[Outreach] Starting outreach flow"})
            # 1) Send emails with ref tokens
            enriched: List[dict] = []
            for c in candidates:
                name = c.get("name") or "there"
                email = c.get("email")
                if not email:
                    continue
                ref = f"{hash((email, subject)) & 0xfffffff:x}"
                body = body_template.format(name=name)
                from tools.communication_tools import CommunicationTools  # type: ignore
                res_json = CommunicationTools.send_email(to=email, subject=subject, body=body, ref_token=ref)
                try:
                    res = json.loads(res_json)
                except Exception:
                    res = {"ok": False, "to": email, "refToken": ref}
                enriched.append({"name": name, "email": email, "refToken": ref, "send": res})
                candidate_store.load([{"name": name, "email": email, "status": "Contacted"}])
                candidate_store.set_ref(email, ref)
                await bus.emit("candidate_status", {"email": email, "status": "Contacted"})
                await bus.emit("log", {"message": f"[Outreach] Sent to {name} <{email}>"})

            await bus.emit("candidates", [
                {"name": e["name"], "email": e["email"], "expertise": "", "status": "Contacted"}
                for e in enriched
            ])

            # 2) Poll for replies within window
            deadline = asyncio.get_event_loop().time() + window_minutes * 60
            scheduled: List[dict] = []
            while asyncio.get_event_loop().time() < deadline:
                for idx, e in enumerate(enriched):
                    if e.get("done"):
                        continue
                    from tools.communication_tools import CommunicationTools  # type: ignore
                    msgs = CommunicationTools.search_replies_by_ref_token(e["refToken"])
                    if msgs:
                        await bus.emit("log", {"message": f"[Outreach] Reply detected from {e['email']}"})
                        meet_json = CommunicationTools.schedule_meeting(
                            attendees=[e["email"]],
                            summary=summary,
                            description=description,
                            duration_minutes=duration,
                            timezone_name=tz,
                        )
                        try:
                            meet = json.loads(meet_json)
                        except Exception:
                            meet = {"eventId": None}
                        e["done"] = True
                        scheduled.append({"email": e["email"], **meet})
                        candidate_store.update_status(e["email"], "Accepted")
                        await bus.emit("candidate_status", {"email": e["email"], "status": "Accepted"})
                        await bus.emit("log", {"message": f"[Scheduling] Meeting created for {e['email']}"})
                await asyncio.sleep(poll_interval)

            await bus.emit("done", {"ok": True, "scheduled": scheduled})
        finally:
            bus.active_run = False

    asyncio.create_task(flow_task())
    return {"ok": True, "status": "started"}


@app.post("/candidates/load")
async def load_candidates(payload: dict = Body(...)) -> dict:
    """Load or overwrite candidates for tracking. Emits SSE update."""
    candidates: List[dict] = payload.get("candidates") or []
    all_recs = candidate_store.load(candidates)
    await bus.emit("candidates", [
        {"name": r.get("name"), "email": r.get("email"), "expertise": r.get("expertise", ""), "status": r.get("status", "Sourced")}
        for r in all_recs
    ])
    return {"ok": True, "count": len(all_recs)}


@app.get("/candidates")
async def list_candidates() -> dict:
    return {"ok": True, "candidates": candidate_store.all()}


@app.patch("/candidates/{email}/status")
async def update_candidate_status(email: str, payload: dict = Body(...)) -> dict:
    status: str = payload.get("status")
    rec = candidate_store.update_status(email, status)
    if rec is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    await bus.emit("candidate_status", {"email": email, "status": status})
    return {"ok": True, "candidate": rec}


@app.post("/speakers/find")
async def find_speakers(payload: dict = Body(...)) -> dict:
    """Find speakers for a given topic and create Google Sheets."""
    try:
        topic = payload.get("topic", "")
        max_results = payload.get("max_results", 20)
        
        if not topic:
            raise HTTPException(status_code=400, detail="Topic is required")
        
        # Use the speaker finder service
        spreadsheet_url = speaker_finder_service.find_and_create_sheet(topic, max_results)
        
        if spreadsheet_url:
            return {
                "ok": True,
                "spreadsheet_url": spreadsheet_url,
                "topic": topic,
                "max_results": max_results,
                "message": f"Successfully created spreadsheet with speakers for '{topic}'"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create spreadsheet")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding speakers: {str(e)}")


@app.get("/speakers/health")
async def speakers_health() -> dict:
    """Health check for speaker finder service."""
    try:
        # Test if the service can be initialized
        return {"ok": True, "service": "speaker_finder", "status": "healthy"}
    except Exception as e:
        return {"ok": False, "service": "speaker_finder", "status": "error", "error": str(e)}

