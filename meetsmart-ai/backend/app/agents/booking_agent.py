"""
Booking Agent
-------------
Given a proposed slot (already validated by the Availability Agent), this
agent re-checks that all participants are still free at that exact time
(protects against race conditions between fetching availability and
confirming), then writes the Meeting row and a ScheduleSlot "Busy" block
for every participant so future availability queries account for it.
"""
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from ..models import Employee, Meeting, ScheduleSlot


class SlotNoLongerAvailableError(Exception):
    pass


def _employee_is_free(db: Session, employee_id: int, start: datetime, end: datetime) -> bool:
    conflict = (
        db.query(ScheduleSlot)
        .filter(
            ScheduleSlot.employee_id == employee_id,
            ScheduleSlot.start_time < end,
            ScheduleSlot.end_time > start,
        )
        .first()
    )
    return conflict is None


def book_meeting(
    db: Session,
    title: str,
    organizer_email: str,
    participant_emails: List[str],
    start_time: datetime,
    end_time: datetime,
    agenda: str = None,
) -> Meeting:
    employees = db.query(Employee).filter(Employee.email.in_(participant_emails)).all()
    if len(employees) != len(participant_emails):
        found = {e.email for e in employees}
        missing = set(participant_emails) - found
        raise ValueError(f"Unknown employee email(s): {missing}")

    # Re-validate the slot is still free for everyone (race-condition guard)
    for emp in employees:
        if not _employee_is_free(db, emp.id, start_time, end_time):
            raise SlotNoLongerAvailableError(
                f"{emp.email} is no longer free at {start_time}–{end_time}"
            )

    meeting = Meeting(
        title=title,
        agenda=agenda,
        organizer_email=organizer_email,
        participant_emails=",".join(participant_emails),
        start_time=start_time,
        end_time=end_time,
        status="confirmed",
    )
    db.add(meeting)
    db.flush()  # get meeting.id before committing

    # Block out this time for every participant so it shows as busy going forward
    for emp in employees:
        db.add(
            ScheduleSlot(
                employee_id=emp.id,
                start_time=start_time,
                end_time=end_time,
                title=title,
            )
        )

    db.commit()
    db.refresh(meeting)
    return meeting
