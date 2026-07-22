# MeetSmart AI — Internal Calendly-Style Meeting Platform

Full-stack agentic meeting-booking platform for ThinkPalm teams — from slot
discovery to post-meeting artefact delivery, using only free tools.

## Architecture (multi-agent)

1. **Availability Agent** — reads/writes SQLite schedule store, surfaces open slots
2. **Booking Agent** — checks all participants' availability, picks optimal slot, confirms booking
3. **Invite Agent** — generates `.ics` invite, sends via SMTP (stubbed for now — see `EMAIL_ENABLED`)
4. **Notes Agent** — ingests transcript/notes text, produces structured notes + action items
5. **MoM Agent** — drafts a formal Minutes of Meeting Word doc, saves it, emails it (stubbed for now)
6. **Reminder Agent** — pre-meeting reminders + post-meeting follow-ups (stubbed for now)

Agents are orchestrated with **LangGraph**.

## Stack

- Backend: FastAPI + SQLite
- Frontend: Streamlit (booking UI)
- LLM: Groq (free LLaMA API) — same as the mini project
- Docs: python-docx, icalendar
- Email: smtplib (stub mode by default)

## Project layout

```
meetsmart-ai/
├── backend/
│   └── app/
│       ├── main.py            # FastAPI app, routes
│       ├── models.py          # SQLAlchemy models
│       ├── database.py        # SQLite engine/session
│       ├── schemas.py         # Pydantic schemas
│       ├── graph.py           # LangGraph orchestration
│       ├── agents/
│       │   ├── availability_agent.py
│       │   ├── booking_agent.py
│       │   ├── invite_agent.py
│       │   ├── notes_agent.py
│       │   ├── mom_agent.py
│       │   └── reminder_agent.py
│       └── db/
│           └── seed.py        # sample employees + schedules
├── frontend/
│   └── app.py                 # Streamlit booking UI
├── samples/                   # sample .ics / MoM outputs land here
├── docs/                      # architecture diagram goes here
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r ../requirements.txt

copy ..\.env.example .env    # then fill in ANTHROPIC_API_KEY
python -m app.db.seed        # seed sample employees + schedules
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
streamlit run app.py
```

## Email / SMTP

Email sending is **stubbed by default** (`EMAIL_ENABLED=false` in `.env`).
Stubbed sends are logged to console and saved under `samples/` instead of
actually emailed. Flip `EMAIL_ENABLED=true` and fill in `SMTP_*` vars once a
Gmail app password is ready — no code changes needed.

## Status

- [x] Project scaffold
- [ ] Availability Agent
- [ ] Booking Agent
- [ ] Invite Agent
- [ ] Notes Agent
- [ ] MoM Agent
- [ ] Reminder Agent
- [ ] LangGraph orchestration
- [ ] Architecture diagram
- [ ] Demo video
