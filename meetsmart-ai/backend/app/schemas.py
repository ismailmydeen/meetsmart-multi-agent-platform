from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class EmployeeOut(BaseModel):
    id: int
    name: str
    email: str
    track: Optional[str] = None

    class Config:
        from_attributes = True


class SlotOut(BaseModel):
    start_time: datetime
    end_time: datetime


class AvailabilityRequest(BaseModel):
    employee_emails: List[str]
    date: str  # YYYY-MM-DD
    duration_minutes: int = 30
    work_start_hour: int = 9
    work_end_hour: int = 18


class AvailabilityResponse(BaseModel):
    date: str
    duration_minutes: int
    common_free_slots: List[SlotOut]


class BookingRequest(BaseModel):
    title: str
    agenda: Optional[str] = None
    organizer_email: str
    participant_emails: List[str]
    start_time: datetime
    end_time: datetime


class BookingResponse(BaseModel):
    meeting_id: int
    title: str
    start_time: datetime
    end_time: datetime
    participant_emails: List[str]
    status: str
    ics_path: Optional[str] = None
    invite_stubbed: Optional[bool] = None


class NotesRequest(BaseModel):
    meeting_id: int
    raw_notes: str


class ActionItemOut(BaseModel):
    description: str
    owner_email: Optional[str] = None
    due_date: Optional[datetime] = None


class NotesResponse(BaseModel):
    meeting_id: int
    summary: str
    action_items: List[ActionItemOut]


class MoMResponse(BaseModel):
    meeting_id: int
    mom_path: str
    stubbed: bool
