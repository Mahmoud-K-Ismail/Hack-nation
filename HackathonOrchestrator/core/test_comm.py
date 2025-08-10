import argparse
import json
import os
from typing import List

from tools.communication_tools import CommunicationTools


def cmd_send_email(args: argparse.Namespace) -> None:
    to = args.to
    subject = args.subject
    body = args.body
    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as f:
            body = f.read()
    result = CommunicationTools.send_email(to=to, subject=subject, body=body)
    print(result)


def cmd_schedule_meeting(args: argparse.Namespace) -> None:
    attendees: List[str] = [e.strip() for e in args.attendees.split(",") if e.strip()]
    result = CommunicationTools.schedule_meeting(
        attendees=attendees,
        summary=args.summary,
        description=args.description,
        start_minutes_from_now=args.start_in,
        duration_minutes=args.duration,
        timezone_name=args.timezone,
        calendar_id=args.calendar_id,
    )
    print(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test Gmail send and Calendar meeting scheduling.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_email = sub.add_parser("email", help="Send a test email via Gmail API")
    p_email.add_argument("--to", required=True, help="Recipient email address")
    p_email.add_argument("--subject", required=True, help="Email subject")
    body_group = p_email.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body", help="Email body (plain text)")
    body_group.add_argument("--body-file", help="Path to a file containing the email body")
    p_email.set_defaults(func=cmd_send_email)

    p_meet = sub.add_parser("meeting", help="Create a Calendar event with Google Meet")
    p_meet.add_argument("--attendees", required=True, help="Comma-separated attendee emails")
    p_meet.add_argument("--summary", default="Hackathon Introductory Meeting", help="Event title")
    p_meet.add_argument("--description", default="Introductory conversation for hackathon speaker/juror onboarding.", help="Event description")
    p_meet.add_argument("--start-in", dest="start_in", type=int, default=60, help="Start offset in minutes from now")
    p_meet.add_argument("--duration", type=int, default=30, help="Duration in minutes")
    p_meet.add_argument("--timezone", default=os.getenv("TIMEZONE", "UTC"), help="Timezone, e.g., UTC or America/Los_Angeles")
    p_meet.add_argument("--calendar-id", dest="calendar_id", default=os.getenv("CALENDAR_ID", "primary"), help="Calendar ID (default primary)")
    p_meet.set_defaults(func=cmd_schedule_meeting)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
