"""
Invite Agent
------------
Auto-generates an iCalendar (.ics) meeting invite with agenda for a booked
meeting, and "sends" it to all participants via SMTP. Email is stubbed by
default (EMAIL_ENABLED=false): the .ics is written to samples/ and the
send is logged instead of actually emailed. Flip EMAIL_ENABLED=true once
SMTP credentials are ready — no code changes needed elsewhere.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from uuid import uuid4

from icalendar import Calendar, Event, vText
from sqlalchemy.orm import Session

from ..models import Meeting

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "samples")
SAMPLES_DIR = os.path.abspath(SAMPLES_DIR)


def generate_ics(meeting: Meeting) -> str:
    """Build an .ics file for the meeting and save it under samples/. Returns the file path."""
    os.makedirs(SAMPLES_DIR, exist_ok=True)

    cal = Calendar()
    cal.add("prodid", "-//MeetSmart AI//meetsmart.thinkpalm.com//")
    cal.add("version", "2.0")

    event = Event()
    event.add("uid", f"{uuid4()}@meetsmart.thinkpalm.com")
    event.add("summary", meeting.title)
    event.add("dtstart", meeting.start_time)
    event.add("dtend", meeting.end_time)
    event.add("dtstamp", datetime.utcnow())
    event.add("organizer", vText(f"mailto:{meeting.organizer_email}"))
    if meeting.agenda:
        event.add("description", meeting.agenda)

    for email in meeting.participant_emails.split(","):
        event.add("attendee", vText(f"mailto:{email.strip()}"))

    cal.add_component(event)

    filename = f"meeting_{meeting.id}_{meeting.start_time.strftime('%Y%m%d_%H%M')}.ics"
    filepath = os.path.join(SAMPLES_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(cal.to_ical())

    return filepath


def send_invite(meeting: Meeting, ics_path: str) -> dict:
    """Send the .ics invite to all participants. Stubbed unless EMAIL_ENABLED=true."""
    email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    recipients = [e.strip() for e in meeting.participant_emails.split(",")]

    if not email_enabled:
        print(f"[STUB EMAIL] Would send invite '{meeting.title}' to {recipients}")
        print(f"[STUB EMAIL] Attachment: {ics_path}")
        return {"sent": False, "stubbed": True, "recipients": recipients, "ics_path": ics_path}

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_APP_PASSWORD")

    msg = MIMEMultipart()
    msg["Subject"] = f"Invite: {meeting.title}"
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)
    body = meeting.agenda or "You have been invited to a meeting."
    msg.attach(MIMEText(body, "plain"))

    with open(ics_path, "rb") as f:
        part = MIMEBase("text", "calendar", method="REQUEST")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(ics_path)}")
        msg.attach(part)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, recipients, msg.as_string())

    return {"sent": True, "stubbed": False, "recipients": recipients, "ics_path": ics_path}


def create_and_send_invite(db: Session, meeting: Meeting) -> dict:
    ics_path = generate_ics(meeting)
    meeting.ics_path = ics_path
    db.commit()
    result = send_invite(meeting, ics_path)
    return result
