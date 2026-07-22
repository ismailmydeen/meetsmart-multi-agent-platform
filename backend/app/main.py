import json
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .database import get_db, Base, engine
from .models import Employee, Meeting, ActionItem
from .schemas import (
    EmployeeOut,
    AvailabilityRequest,
    AvailabilityResponse,
    SlotOut,
    BookingRequest,
    BookingResponse,
    NotesRequest,
    NotesResponse,
    ActionItemOut,
    MoMResponse,
    ReminderResponse,
    ReminderResult,
    OrchestrateBookingRequest,
    OrchestratePostMeetingRequest,
)
from .agents.availability_agent import find_common_free_slots
from .agents.booking_agent import book_meeting, SlotNoLongerAvailableError
from .agents.invite_agent import create_and_send_invite
from .agents.notes_agent import structure_notes
from .agents.mom_agent import create_and_send_mom
from .agents.reminder_agent import send_pre_meeting_reminders, send_post_meeting_followups
from .graph import booking_graph, post_meeting_graph

Base.metadata.create_all(bind=engine)

app = FastAPI(title="MeetSmart AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/employees", response_model=List[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    return db.query(Employee).all()


@app.post("/availability", response_model=AvailabilityResponse)
def get_availability(req: AvailabilityRequest, db: Session = Depends(get_db)):
    slots = find_common_free_slots(
        db,
        employee_emails=req.employee_emails,
        date_str=req.date,
        duration_minutes=req.duration_minutes,
        work_start_hour=req.work_start_hour,
        work_end_hour=req.work_end_hour,
    )
    return AvailabilityResponse(
        date=req.date,
        duration_minutes=req.duration_minutes,
        common_free_slots=[SlotOut(start_time=s, end_time=e) for s, e in slots],
    )


@app.post("/book", response_model=BookingResponse)
def book(req: BookingRequest, db: Session = Depends(get_db)):
    # Booking Agent re-validates the exact chosen slot is still free for
    # everyone (protects against a race between /availability and /book).
    try:
        meeting = book_meeting(
            db,
            title=req.title,
            organizer_email=req.organizer_email,
            participant_emails=[req.organizer_email] + req.participant_emails,
            start_time=req.start_time,
            end_time=req.end_time,
            agenda=req.agenda,
        )
    except SlotNoLongerAvailableError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    invite_result = create_and_send_invite(db, meeting)

    return BookingResponse(
        meeting_id=meeting.id,
        title=meeting.title,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        participant_emails=meeting.participant_emails.split(","),
        status=meeting.status,
        ics_path=invite_result["ics_path"],
        invite_stubbed=invite_result["stubbed"],
    )


@app.post("/notes", response_model=NotesResponse)
def process_notes(req: NotesRequest, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == req.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    participant_emails = meeting.participant_emails.split(",")
    structured = structure_notes(req.raw_notes, participant_emails)

    meeting.notes_raw = req.raw_notes
    meeting.notes_structured = json.dumps(structured)
    db.commit()

    action_items_out = []
    for item in structured.get("action_items", []):
        due = None
        if item.get("due_date"):
            try:
                due = datetime.strptime(item["due_date"], "%Y-%m-%d")
            except ValueError:
                due = None

        db.add(
            ActionItem(
                meeting_id=meeting.id,
                description=item.get("description", ""),
                owner_email=item.get("owner_email"),
                due_date=due,
                status="pending",
            )
        )
        action_items_out.append(
            ActionItemOut(
                description=item.get("description", ""),
                owner_email=item.get("owner_email"),
                due_date=due,
            )
        )
    db.commit()

    return NotesResponse(
        meeting_id=meeting.id,
        summary=structured.get("summary", ""),
        action_items=action_items_out,
    )


@app.post("/mom/{meeting_id}", response_model=MoMResponse)
def generate_mom(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not meeting.notes_structured:
        raise HTTPException(
            status_code=400,
            detail="No structured notes yet for this meeting — run /notes first.",
        )

    result = create_and_send_mom(db, meeting)

    return MoMResponse(
        meeting_id=meeting.id,
        mom_path=result["mom_path"],
        stubbed=result["stubbed"],
    )


@app.post("/reminders/pre-meeting/{meeting_id}", response_model=ReminderResponse)
def pre_meeting_reminder(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    results = send_pre_meeting_reminders(db, meeting)
    return ReminderResponse(
        meeting_id=meeting.id,
        results=[ReminderResult(**r) for r in results],
    )


@app.post("/reminders/follow-up/{meeting_id}", response_model=ReminderResponse)
def post_meeting_followup(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    results = send_post_meeting_followups(db, meeting)
    return ReminderResponse(
        meeting_id=meeting.id,
        results=[ReminderResult(**r) for r in results],
    )


# ---------------------------------------------------------------------------
# LangGraph orchestration endpoints — run the multi-agent graphs end to end
# ---------------------------------------------------------------------------

@app.get("/export/action-items")
def export_action_items(format: str = "json", db: Session = Depends(get_db)):
    """Action-item tracker export — all action items across all meetings,
    as JSON (default) or CSV (?format=csv)."""
    items = db.query(ActionItem).order_by(ActionItem.meeting_id, ActionItem.id).all()

    rows = []
    for item in items:
        meeting = db.query(Meeting).filter(Meeting.id == item.meeting_id).first()
        rows.append(
            {
                "meeting_id": item.meeting_id,
                "meeting_title": meeting.title if meeting else None,
                "action_item_id": item.id,
                "description": item.description,
                "owner_email": item.owner_email,
                "due_date": item.due_date.strftime("%Y-%m-%d") if item.due_date else None,
                "status": item.status,
            }
        )

    if format == "csv":
        import csv
        import io
        from fastapi.responses import StreamingResponse

        buffer = io.StringIO()
        fieldnames = ["meeting_id", "meeting_title", "action_item_id", "description", "owner_email", "due_date", "status"]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        buffer.seek(0)

        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=action_items.csv"},
        )

    return rows
def orchestrate_book(req: OrchestrateBookingRequest, db: Session = Depends(get_db)):
    """Runs Availability -> Booking -> Invite as a single LangGraph graph,
    auto-picking the first common free slot on the given date."""
    result = booking_graph.invoke(
        {
            "db": db,
            "title": req.title,
            "agenda": req.agenda,
            "organizer_email": req.organizer_email,
            "participant_emails": req.participant_emails,
            "date": req.date,
            "duration_minutes": req.duration_minutes,
            "work_start_hour": req.work_start_hour,
            "work_end_hour": req.work_end_hour,
        }
    )

    if result.get("error"):
        raise HTTPException(status_code=409, detail=result["error"])

    meeting = result["meeting"]
    invite = result.get("invite_result") or {}
    return {
        "meeting_id": meeting.id,
        "title": meeting.title,
        "start_time": meeting.start_time,
        "end_time": meeting.end_time,
        "participant_emails": meeting.participant_emails.split(","),
        "ics_path": invite.get("ics_path"),
        "invite_stubbed": invite.get("stubbed"),
    }


@app.post("/orchestrate/post-meeting")
def orchestrate_post_meeting(req: OrchestratePostMeetingRequest, db: Session = Depends(get_db)):
    """Runs Notes -> MoM -> Reminders as a single LangGraph graph."""
    meeting = db.query(Meeting).filter(Meeting.id == req.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    result = post_meeting_graph.invoke(
        {"db": db, "meeting": meeting, "raw_notes": req.raw_notes}
    )

    return {
        "meeting_id": meeting.id,
        "summary": result["structured_notes"].get("summary"),
        "action_items": result["structured_notes"].get("action_items"),
        "mom_path": result["mom_result"]["mom_path"],
        "mom_stubbed": result["mom_result"]["stubbed"],
        "followups_sent": len(result.get("followup_results") or []),
    }
