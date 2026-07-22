"""
LangGraph Orchestration
------------------------
Wires the six agents into two graphs:

1. booking_graph — Availability → Booking → Invite
   Given participants + a date, finds the first common free slot,
   books it, and generates/sends the .ics invite, end to end.

2. post_meeting_graph — Notes → MoM → Reminders
   Given a meeting_id + raw notes, structures them, drafts the MoM,
   and sends pending-action-item follow-ups, end to end.

The interactive Streamlit UI calls agents directly (via the FastAPI
routes) so the user can pick a specific slot and review notes before
committing — these graphs are the autonomous, one-shot orchestration
path described in the project spec, exposed via /orchestrate/* routes.
"""
from typing import TypedDict, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from .agents.availability_agent import find_common_free_slots
from .agents.booking_agent import book_meeting, SlotNoLongerAvailableError
from .agents.invite_agent import create_and_send_invite
from .agents.notes_agent import structure_notes
from .agents.mom_agent import create_and_send_mom
from .agents.reminder_agent import send_post_meeting_followups
from .models import Meeting, ActionItem


# ---------------------------------------------------------------------------
# 1. Booking graph: Availability Agent -> Booking Agent -> Invite Agent
# ---------------------------------------------------------------------------

class BookingState(TypedDict, total=False):
    db: Session
    title: str
    agenda: Optional[str]
    organizer_email: str
    participant_emails: List[str]
    date: str
    duration_minutes: int
    work_start_hour: int
    work_end_hour: int
    slot: Optional[tuple]
    meeting: Optional[Meeting]
    invite_result: Optional[dict]
    error: Optional[str]


def _node_find_availability(state: BookingState) -> BookingState:
    all_emails = [state["organizer_email"]] + state["participant_emails"]
    slots = find_common_free_slots(
        state["db"],
        employee_emails=all_emails,
        date_str=state["date"],
        duration_minutes=state.get("duration_minutes", 30),
        work_start_hour=state.get("work_start_hour", 9),
        work_end_hour=state.get("work_end_hour", 18),
    )
    if not slots:
        return {**state, "error": "No common free slots found for that date."}
    return {**state, "slot": slots[0]}


def _node_book(state: BookingState) -> BookingState:
    if state.get("error"):
        return state
    start, end = state["slot"]
    try:
        meeting = book_meeting(
            state["db"],
            title=state["title"],
            organizer_email=state["organizer_email"],
            participant_emails=[state["organizer_email"]] + state["participant_emails"],
            start_time=start,
            end_time=end,
            agenda=state.get("agenda"),
        )
        return {**state, "meeting": meeting}
    except (SlotNoLongerAvailableError, ValueError) as e:
        return {**state, "error": str(e)}


def _node_invite(state: BookingState) -> BookingState:
    if state.get("error") or not state.get("meeting"):
        return state
    result = create_and_send_invite(state["db"], state["meeting"])
    return {**state, "invite_result": result}


def _route_after_availability(state: BookingState) -> str:
    return "book" if not state.get("error") else END


def _route_after_booking(state: BookingState) -> str:
    return "invite" if not state.get("error") else END


def build_booking_graph():
    graph = StateGraph(BookingState)
    graph.add_node("find_availability", _node_find_availability)
    graph.add_node("book", _node_book)
    graph.add_node("invite", _node_invite)

    graph.set_entry_point("find_availability")
    graph.add_conditional_edges("find_availability", _route_after_availability, {"book": "book", END: END})
    graph.add_conditional_edges("book", _route_after_booking, {"invite": "invite", END: END})
    graph.add_edge("invite", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# 2. Post-meeting graph: Notes Agent -> MoM Agent -> Reminder Agent
# ---------------------------------------------------------------------------

class PostMeetingState(TypedDict, total=False):
    db: Session
    meeting: Meeting
    raw_notes: str
    structured_notes: Optional[dict]
    mom_result: Optional[dict]
    followup_results: Optional[list]
    error: Optional[str]


def _node_structure_notes(state: PostMeetingState) -> PostMeetingState:
    import json

    meeting = state["meeting"]
    participant_emails = meeting.participant_emails.split(",")
    structured = structure_notes(state["raw_notes"], participant_emails)

    meeting.notes_raw = state["raw_notes"]
    meeting.notes_structured = json.dumps(structured)
    state["db"].commit()

    for item in structured.get("action_items", []):
        due = None
        if item.get("due_date"):
            try:
                due = datetime.strptime(item["due_date"], "%Y-%m-%d")
            except ValueError:
                due = None
        state["db"].add(
            ActionItem(
                meeting_id=meeting.id,
                description=item.get("description", ""),
                owner_email=item.get("owner_email"),
                due_date=due,
                status="pending",
            )
        )
    state["db"].commit()

    return {**state, "structured_notes": structured}


def _node_generate_mom(state: PostMeetingState) -> PostMeetingState:
    result = create_and_send_mom(state["db"], state["meeting"])
    return {**state, "mom_result": result}


def _node_followups(state: PostMeetingState) -> PostMeetingState:
    results = send_post_meeting_followups(state["db"], state["meeting"])
    return {**state, "followup_results": results}


def build_post_meeting_graph():
    graph = StateGraph(PostMeetingState)
    graph.add_node("structure_notes", _node_structure_notes)
    graph.add_node("generate_mom", _node_generate_mom)
    graph.add_node("followups", _node_followups)

    graph.set_entry_point("structure_notes")
    graph.add_edge("structure_notes", "generate_mom")
    graph.add_edge("generate_mom", "followups")
    graph.add_edge("followups", END)

    return graph.compile()


# Compiled once at import time, reused across requests
booking_graph = build_booking_graph()
post_meeting_graph = build_post_meeting_graph()
