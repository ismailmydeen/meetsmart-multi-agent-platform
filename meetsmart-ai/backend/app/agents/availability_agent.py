"""
Availability Agent
-------------------
Reads the SQLite schedule store and surfaces open slots for one or more
employees on a given date. Logic: build each employee's busy intervals for
the day, invert against working hours to get free intervals, then intersect
free intervals across all employees to find common slots.
"""
from datetime import datetime, timedelta, time
from typing import List, Tuple
from sqlalchemy.orm import Session

from ..models import Employee, ScheduleSlot


def _get_busy_intervals(db: Session, employee_id: int, day: datetime.date) -> List[Tuple[datetime, datetime]]:
    day_start = datetime.combine(day, time.min)
    day_end = datetime.combine(day, time.max)

    slots = (
        db.query(ScheduleSlot)
        .filter(
            ScheduleSlot.employee_id == employee_id,
            ScheduleSlot.start_time < day_end,
            ScheduleSlot.end_time > day_start,
        )
        .order_by(ScheduleSlot.start_time)
        .all()
    )
    return [(s.start_time, s.end_time) for s in slots]


def _free_intervals(
    busy: List[Tuple[datetime, datetime]],
    work_start: datetime,
    work_end: datetime,
) -> List[Tuple[datetime, datetime]]:
    """Invert busy intervals against the working-hours window."""
    free = []
    cursor = work_start
    for start, end in sorted(busy):
        if start > cursor:
            free.append((cursor, min(start, work_end)))
        cursor = max(cursor, end)
        if cursor >= work_end:
            break
    if cursor < work_end:
        free.append((cursor, work_end))
    return [f for f in free if f[1] > f[0]]


def _intersect(a: List[Tuple[datetime, datetime]], b: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    result = []
    i = j = 0
    while i < len(a) and j < len(b):
        start = max(a[i][0], b[j][0])
        end = min(a[i][1], b[j][1])
        if start < end:
            result.append((start, end))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return result


def find_common_free_slots(
    db: Session,
    employee_emails: List[str],
    date_str: str,
    duration_minutes: int = 30,
    work_start_hour: int = 9,
    work_end_hour: int = 18,
) -> List[Tuple[datetime, datetime]]:
    day = datetime.strptime(date_str, "%Y-%m-%d").date()
    work_start = datetime.combine(day, time(hour=work_start_hour))
    work_end = datetime.combine(day, time(hour=work_end_hour))

    employees = db.query(Employee).filter(Employee.email.in_(employee_emails)).all()
    if not employees:
        return []

    common: List[Tuple[datetime, datetime]] = [(work_start, work_end)]
    for emp in employees:
        busy = _get_busy_intervals(db, emp.id, day)
        free = _free_intervals(busy, work_start, work_end)
        common = _intersect(common, free)
        if not common:
            return []

    # Split common free windows into bookable chunks of `duration_minutes`
    duration = timedelta(minutes=duration_minutes)
    bookable = []
    for start, end in common:
        cursor = start
        while cursor + duration <= end:
            bookable.append((cursor, cursor + duration))
            cursor += duration
    return bookable
