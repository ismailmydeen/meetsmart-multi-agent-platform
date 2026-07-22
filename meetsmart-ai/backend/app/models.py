from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    track = Column(String, nullable=True)  # Backend / QA / PM / etc.


class ScheduleSlot(Base):
    """A block of time an employee is BUSY. Anything not listed is free."""
    __tablename__ = "schedule_slots"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    title = Column(String, default="Busy")

    employee = relationship("Employee")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    agenda = Column(Text, nullable=True)
    organizer_email = Column(String, nullable=False)
    participant_emails = Column(Text, nullable=False)  # comma-separated
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, default="confirmed")  # confirmed / cancelled
    ics_path = Column(String, nullable=True)
    mom_path = Column(String, nullable=True)
    notes_raw = Column(Text, nullable=True)
    notes_structured = Column(Text, nullable=True)  # JSON string


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    description = Column(Text, nullable=False)
    owner_email = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending / done

    meeting = relationship("Meeting")
