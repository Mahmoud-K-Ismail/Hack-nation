import base64
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import uuid4

from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow

from crewai_tools import BaseTool


GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CAL_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
TOKEN_GMAIL = os.path.join(os.path.dirname(os.path.dirname(__file__)), "token_gmail.json")
TOKEN_CAL = os.path.join(os.path.dirname(os.path.dirname(__file__)), "token_calendar.json")


def _load_credentials(scopes: List[str], token_path: str) -> Credentials:
    creds: Optional[Credentials] = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Missing Google OAuth client secrets at {CREDENTIALS_PATH}. "
                    "Download OAuth 2.0 Client IDs JSON and save as credentials.json."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())
    return creds


def _get_gmail_service():
    creds = _load_credentials(GMAIL_SCOPES, TOKEN_GMAIL)
    return build("gmail", "v1", credentials=creds)


def _get_calendar_service():
    creds = _load_credentials(CAL_SCOPES, TOKEN_CAL)
    return build("calendar", "v3", credentials=creds)


class CommunicationTools:
    @staticmethod
    def send_email(to: str, subject: str, body: str) -> str:
        """Send an email using Gmail API.

        Requires credentials.json and first-time OAuth authorization.
        Uses env SENDER_EMAIL for From, falling back to the authenticated account.
        """
        try:
            service = _get_gmail_service()

            message = EmailMessage()
            sender = os.getenv("SENDER_EMAIL", "me")
            message["To"] = to
            message["From"] = sender
            message["Subject"] = subject
            message.set_content(body)

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_body = {"raw": encoded_message}

            sent = (
                service.users()
                .messages()
                .send(userId="me", body=send_body)
                .execute()
            )
            msg_id = sent.get("id")
            print("\n--- GMAIL ---")
            print(f"Email sent. Message ID: {msg_id}")
            return f"Email successfully sent to {to}. Message ID: {msg_id}"
        except HttpError as e:
            raise RuntimeError(f"Gmail API error: {e}") from e

    @staticmethod
    def schedule_meeting(
        attendees: List[str],
        summary: Optional[str] = None,
        description: Optional[str] = None,
        start_minutes_from_now: int = 60,
        duration_minutes: int = 30,
        timezone_name: Optional[str] = None,
        calendar_id: Optional[str] = None,
    ) -> str:
        """Create a Google Calendar event with a Meet link.

        - attendees: list of attendee emails
        - summary: event title (default: "Hackathon Introductory Meeting")
        - description: event description
        - start_minutes_from_now: when to start from now (default: 60)
        - duration_minutes: meeting duration (default: 30)
        - timezone_name: e.g., "UTC" or "America/Los_Angeles" (default: env TIMEZONE or UTC)
        - calendar_id: calendar to use (default: env CALENDAR_ID or "primary")
        """
        try:
            service = _get_calendar_service()
            now_utc = datetime.now(timezone.utc)
            start_dt = now_utc + timedelta(minutes=int(start_minutes_from_now))
            end_dt = start_dt + timedelta(minutes=int(duration_minutes))

            tz = timezone_name or os.getenv("TIMEZONE", "UTC")
            cal_id = calendar_id or os.getenv("CALENDAR_ID", "primary")

            event_body = {
                "summary": summary or "Hackathon Introductory Meeting",
                "description": description or "Introductory conversation for hackathon speaker/juror onboarding.",
                "start": {"dateTime": start_dt.isoformat(), "timeZone": tz},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": tz},
                "attendees": [{"email": email} for email in attendees],
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(uuid4()),
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
            }

            created = (
                service.events()
                .insert(calendarId=cal_id, body=event_body, conferenceDataVersion=1)
                .execute()
            )

            html_link = created.get("htmlLink")
            meet_link = None
            conf = created.get("conferenceData", {})
            if conf and conf.get("entryPoints"):
                for ep in conf["entryPoints"]:
                    if ep.get("entryPointType") == "video":
                        meet_link = ep.get("uri")
                        break

            event_id = created.get("id")
            print("\n--- CALENDAR ---")
            print(f"Event created. ID: {event_id}")
            print(f"Calendar link: {html_link}")
            if meet_link:
                print(f"Meet link: {meet_link}")

            result_summary = {
                "eventId": event_id,
                "calendarLink": html_link,
                "meetLink": meet_link,
            }
            return json.dumps(result_summary)
        except HttpError as e:
            raise RuntimeError(f"Calendar API error: {e}") from e


class SendEmailTool(BaseTool):
    name: str = "Send Outreach Email"
    description: str = "Sends a personalized outreach email to a potential candidate."

    def _run(self, to: str, subject: str, body: str) -> str:
        return CommunicationTools.send_email(to, subject, body)


class ScheduleMeetingTool(BaseTool):
    name: str = "Schedule Introductory Meeting"
    description: str = (
        "Schedules a 30-minute introductory meeting with a confirmed candidate (Google Meet)."
    )

    def _run(self, attendees: List[str]) -> str:
        return CommunicationTools.schedule_meeting(attendees)
