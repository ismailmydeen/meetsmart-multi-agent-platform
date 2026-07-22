"""
Reminder Agent
--------------
Sends pre-meeting reminders to all participants, and post-meeting
follow-ups to the owner of each still-pending action item. Email is
stubbed by default (EMAIL_ENABLED=false), same convention as the
Invite and MoM Agents — logged + returned instead of actually sent.

In a real deployment this would be triggered by a scheduler (cron /
APScheduler) checking meetings starting soon or action items overdue.
Here it's exposed as callable functions + endpoints so it can be
triggered on demand for the demo.
"""
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session

from ..models import Meeting, ActionItem


def _send_email(to_email: str, subject: str, body: str) -> dict:
    email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

    if not email_enabled:
        print(f"[STUB EMAIL] To: {to_email} | Subject: {subject}")
        print(f"[STUB EMAIL] Body: {body}")
        return {"sent": False, "stubbed": True, "to": to_email, "subject": subject}

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_APP_PASSWORD")

    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())

    return {"sent": True, "stubbed": False, "to": to_email, "subject": subject}


def send_pre_meeting_reminders(db: Session, meeting: Meeting) -> List[Dict]:
    """Notify every participant that the meeting is coming up."""
    results = []
    subject = f"Reminder: '{meeting.title}' starts soon"
    body = (
        f"This is a reminder that '{meeting.title}' is scheduled for "
        f"{meeting.start_time.strftime('%d %b %Y, %H:%M')}–{meeting.end_time.strftime('%H:%M')}.\n\n"
        f"Agenda: {meeting.agenda or 'N/A'}"
    )
    for email in meeting.participant_emails.split(","):
        results.append(_send_email(email.strip(), subject, body))
    return results


def send_post_meeting_followups(db: Session, meeting: Meeting) -> List[Dict]:
    """Nudge the owner of each still-pending action item from this meeting."""
    pending_items = (
        db.query(ActionItem)
        .filter(ActionItem.meeting_id == meeting.id, ActionItem.status == "pending")
        .all()
    )

    results = []
    for item in pending_items:
        if not item.owner_email:
            continue
        due = item.due_date.strftime("%d %b %Y") if item.due_date else "no due date set"
        subject = f"Follow-up: action item from '{meeting.title}'"
        body = (
            f"This is a follow-up on an action item from '{meeting.title}' "
            f"({meeting.start_time.strftime('%d %b %Y')}):\n\n"
            f"- {item.description} (due {due})\n\n"
            f"Please update its status when complete."
        )
        result = _send_email(item.owner_email, subject, body)
        result["action_item"] = item.description
        results.append(result)

    return results
