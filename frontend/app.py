import streamlit as st
import requests
from datetime import date, timedelta

API_URL = "http://localhost:8000"

st.set_page_config(page_title="MeetSmart AI", page_icon="🗓️", layout="wide")

# ---------------------------------------------------------------------------
# Design system: warm, friendly "scheduling assistant" look. Soft gradient
# hero, colorful per-agent badges, pastel-themed cards per workflow stage.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stAppViewContainer"] { background: #EEF2F9; }
[data-testid="stHeader"] { background: transparent; }

h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; color: #0F2A3D !important; letter-spacing: -0.01em; }
h2, h3 { font-weight: 600 !important; }

/* Hero — deep teal-to-blue with glow */
.msa-hero {
    background: linear-gradient(135deg, #0D5C63 0%, #14487A 60%, #1B3B6F 100%);
    border-radius: 22px;
    padding: 38px 42px 32px 42px;
    margin-bottom: 26px;
    box-shadow:
        0 20px 40px -10px rgba(13,92,99,0.45),
        0 2px 0 rgba(255,255,255,0.08) inset,
        0 -30px 60px -30px rgba(255,255,255,0.12) inset;
    position: relative;
    overflow: hidden;
}
.msa-hero::after {
    content: ""; position: absolute; top: -60px; right: -60px;
    width: 220px; height: 220px; border-radius: 50%;
    background: radial-gradient(circle, rgba(255,183,77,0.35), transparent 70%);
}
.msa-hero h1 { color: white !important; margin: 0 0 4px 0; font-size: 2.15rem !important;
    text-shadow: 0 2px 8px rgba(0,0,0,0.25); }
.msa-hero p { color: rgba(255,255,255,0.88); margin: 0 0 20px 0; font-size: 1rem; }

.agent-row { display: flex; gap: 10px; flex-wrap: wrap; position: relative; z-index: 1; }
.agent-chip {
    display: flex; align-items: center; gap: 6px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.28);
    border-radius: 24px;
    padding: 7px 14px 7px 10px;
    font-size: 0.85rem; font-weight: 600; color: white;
    backdrop-filter: blur(6px);
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.agent-chip.done {
    background: linear-gradient(135deg, #FFB74D, #FF8F3D);
    border-color: transparent; color: #3D2200;
    box-shadow: 0 3px 10px rgba(255,143,61,0.5), 0 1px 0 rgba(255,255,255,0.5) inset;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] {
    font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 0.95rem;
    color: #5C7185; padding: 10px 6px;
}
.stTabs [aria-selected="true"] { color: #0D5C63 !important; }

/* Cards — real elevation with layered shadows */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, #FFFFFF, #FBFCFE);
    border-radius: 18px !important;
    border: 1px solid #E4E9F2 !important;
    box-shadow:
        0 1px 2px rgba(15,42,61,0.04),
        0 12px 24px -12px rgba(15,42,61,0.14),
        0 1px 0 rgba(255,255,255,0.8) inset;
}

.card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
.card-header .icon {
    width: 42px; height: 42px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem; position: relative;
    box-shadow:
        0 4px 10px -2px rgba(15,42,61,0.35),
        0 1px 0 rgba(255,255,255,0.5) inset;
}
.icon-blue { background: linear-gradient(145deg, #4FA8E0, #1D6FA8); }
.icon-purple { background: linear-gradient(145deg, #A56EE8, #6B3FB8); }
.icon-orange { background: linear-gradient(145deg, #FFB74D, #E8792E); }
.icon-green { background: linear-gradient(145deg, #4FD69C, #14A876); }

/* Buttons — raised, glowing gold primary */
.stButton > button {
    border-radius: 12px; font-weight: 700; font-size: 0.92rem;
    border: 1px solid #E4E9F2; padding: 0.55rem 1.1rem;
    transition: all 0.15s ease;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(160deg, #FFC266, #FF8F3D 70%, #F2701A);
    border: none; color: #3D2200;
    box-shadow:
        0 6px 14px -4px rgba(242,112,26,0.55),
        0 1px 0 rgba(255,255,255,0.6) inset;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 9px 18px -4px rgba(242,112,26,0.65), 0 1px 0 rgba(255,255,255,0.6) inset;
}
.stButton > button[kind="primary"]:active { transform: translateY(1px); }
.stButton > button[kind="secondary"] { background: #F3F6FA; color: #0F2A3D; }
.stButton > button[kind="secondary"]:hover { background: #E4E9F2; }

/* Slot picker pills — raised / pressed-in when selected */
div[role="radiogroup"] { gap: 8px; }
div[role="radiogroup"] label {
    border: 1px solid #E4E9F2; background: linear-gradient(180deg, #FFFFFF, #F6F8FB);
    border-radius: 12px;
    padding: 9px 17px !important; margin-right: 4px !important;
    font-weight: 700; font-size: 0.88rem; color: #33465A;
    box-shadow: 0 2px 5px -1px rgba(15,42,61,0.12), 0 1px 0 rgba(255,255,255,0.6) inset;
    transition: all 0.15s ease;
}
div[role="radiogroup"] label:hover { border-color: #1D6FA8; }
div[role="radiogroup"] label:has(input:checked) {
    border-color: transparent;
    background: linear-gradient(160deg, #14A876, #0D5C63);
    color: white !important;
    box-shadow: 0 2px 6px -1px rgba(13,92,99,0.5) inset, 0 3px 8px -2px rgba(13,92,99,0.4);
}
div[role="radiogroup"] label:has(input:checked) p { color: white !important; }

.eyebrow {
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: #0D5C63; margin-bottom: 2px;
}
.helper-text { color: #6B7C8C; font-size: 0.88rem; margin-top: -6px; }

[data-testid="stMetric"] {
    background: linear-gradient(180deg, #FFFFFF, #F6F8FB);
    border-radius: 14px; padding: 12px 16px;
    border: 1px solid #E4E9F2;
    box-shadow: 0 4px 10px -4px rgba(15,42,61,0.12);
}
</style>
""", unsafe_allow_html=True)


# --- Load employees ---
try:
    employees = requests.get(f"{API_URL}/employees").json()
except requests.exceptions.ConnectionError:
    st.error("Backend not reachable. Start it with `uvicorn app.main:app --reload --port 8000`.")
    st.stop()

email_by_name = {e["name"]: e["email"] for e in employees}

# --- Pipeline status flags ---
booked = "last_meeting_id" in st.session_state
notes_done = "notes_result" in st.session_state
mom_done = "mom_result" in st.session_state
reminders_done = st.session_state.get("reminders_sent", False)

agents = [
    ("🗓️", "Availability", True),
    ("📌", "Booking", booked),
    ("✉️", "Invite", booked),
    ("📝", "Notes", notes_done),
    ("📄", "MoM", mom_done),
    ("🔔", "Reminder", reminders_done),
]
chips = "".join(
    f'<span class="agent-chip{" done" if done else ""}"><span class="dot">{icon}</span>{name}</span>'
    for icon, name, done in agents
)

st.markdown(f"""
<div class="msa-hero">
    <h1>🗓️ MeetSmart AI</h1>
    <p>Your internal scheduling assistant — find a time, book it, and let six agents handle the rest.</p>
    <div class="agent-row">{chips}</div>
</div>
""", unsafe_allow_html=True)

tab_book, tab_notes, tab_reminders, tab_export = st.tabs(
    ["📅  Book a meeting", "📝  Notes & Minutes", "🔔  Reminders", "📊  Export"]
)

# ---------------------------------------------------------------------------
# TAB 1 — Book a meeting
# ---------------------------------------------------------------------------
with tab_book:
    with st.container(border=True):
        st.markdown(
            '<div class="card-header"><div class="icon icon-blue">🗓️</div>'
            '<div><div class="eyebrow">Availability Agent</div>'
            '<h3 style="margin:0;">Who\'s meeting, and when?</h3></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="helper-text">Pick everyone who needs to be there — we\'ll find a time that works for all of them.</p>', unsafe_allow_html=True)
        st.write("")

        col1, col2 = st.columns([2, 1])
        with col1:
            selected_names = st.multiselect("Employees", list(email_by_name.keys()), placeholder="Choose participants...")
        with col2:
            duration = st.selectbox("Duration", [15, 30, 45, 60], index=1, format_func=lambda m: f"{m} min")

        meeting_date = st.date_input("Date", value=date.today() + timedelta(days=1))

        if st.button("🔍  Find available slots", type="primary"):
            if not selected_names:
                st.warning("Pick at least one participant first.")
            else:
                emails = [email_by_name[n] for n in selected_names]
                resp = requests.post(
                    f"{API_URL}/availability",
                    json={
                        "employee_emails": emails,
                        "date": meeting_date.strftime("%Y-%m-%d"),
                        "duration_minutes": duration,
                    },
                )
                data = resp.json()
                st.session_state["slots"] = data["common_free_slots"]

    if "slots" in st.session_state:
        slots = st.session_state["slots"]
        st.write("")
        with st.container(border=True):
            st.markdown(
                '<div class="card-header"><div class="icon icon-green">✅</div>'
                '<div><div class="eyebrow">Booking Agent · Invite Agent</div>'
                '<h3 style="margin:0;">Pick a time & confirm</h3></div></div>',
                unsafe_allow_html=True,
            )
            st.write("")
            if not slots:
                st.info("😕 No common free slot on that day — try a different date or fewer participants.")
            else:
                labels = [f"{s['start_time'][11:16]} – {s['end_time'][11:16]}" for s in slots]
                choice_idx = st.radio(
                    "Available slots", range(len(labels)), format_func=lambda i: labels[i],
                    horizontal=True, label_visibility="collapsed",
                )

                col_a, col_b = st.columns(2)
                with col_a:
                    meeting_title = st.text_input("Meeting title", value="Sync-up")
                with col_b:
                    st.write("")

                agenda = st.text_area("Agenda (optional)", value="", placeholder="What's this meeting about?")

                if st.button("✅  Confirm booking", type="primary"):
                    chosen = slots[choice_idx]
                    organizer_email = email_by_name[selected_names[0]]
                    other_participants = [email_by_name[n] for n in selected_names[1:]]

                    resp = requests.post(
                        f"{API_URL}/book",
                        json={
                            "title": meeting_title,
                            "agenda": agenda or None,
                            "organizer_email": organizer_email,
                            "participant_emails": other_participants,
                            "start_time": chosen["start_time"],
                            "end_time": chosen["end_time"],
                        },
                    )
                    if resp.status_code == 200:
                        booking = resp.json()
                        st.success(
                            f"🎉 Booked! Meeting #{booking['meeting_id']} — "
                            f"{booking['start_time'][11:16]}–{booking['end_time'][11:16]} "
                            f"with {', '.join(booking['participant_emails'])}"
                        )
                        if booking.get("ics_path"):
                            st.info(f"📎 Calendar invite generated: `{booking['ics_path']}`")
                            if booking.get("invite_stubbed"):
                                st.caption("✉️ Email sending is stubbed — invite was saved to samples/ instead of emailed.")
                        st.session_state["last_meeting_id"] = booking["meeting_id"]
                        del st.session_state["slots"]
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"Booking failed: {resp.json().get('detail', resp.text)}")

# ---------------------------------------------------------------------------
# TAB 2 — Notes & Minutes
# ---------------------------------------------------------------------------
with tab_notes:
    with st.container(border=True):
        st.markdown(
            '<div class="card-header"><div class="icon icon-purple">📝</div>'
            '<div><div class="eyebrow">Notes Agent · Groq LLaMA</div>'
            '<h3 style="margin:0;">Turn raw notes into a clean summary</h3></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="helper-text">Paste anything — a transcript, bullet points, a rough recap — and we\'ll extract action items automatically.</p>', unsafe_allow_html=True)
        st.write("")

        default_meeting_id = st.session_state.get("last_meeting_id", 1)
        meeting_id = st.number_input("Meeting ID", min_value=1, value=default_meeting_id, step=1)
        raw_notes = st.text_area(
            "Paste meeting transcript / raw notes",
            placeholder="e.g. Priya will update the test plan by Friday. Ismail to review PR #42 tomorrow...",
            height=150,
        )

        if st.button("✨  Generate structured notes", type="primary"):
            if not raw_notes.strip():
                st.warning("Paste some notes first.")
            else:
                with st.spinner("Reading through your notes..."):
                    resp = requests.post(
                        f"{API_URL}/notes",
                        json={"meeting_id": int(meeting_id), "raw_notes": raw_notes},
                    )
                if resp.status_code == 200:
                    st.session_state["notes_result"] = resp.json()
                    st.session_state["notes_meeting_id"] = int(meeting_id)
                else:
                    st.error(f"Failed: {resp.json().get('detail', resp.text)}")

    if "notes_result" in st.session_state:
        data = st.session_state["notes_result"]
        st.write("")
        with st.container(border=True):
            st.markdown('<div class="eyebrow">Summary</div>', unsafe_allow_html=True)
            st.write(data["summary"])

            if data["action_items"]:
                st.markdown('<div class="eyebrow" style="margin-top:14px;">Action items</div>', unsafe_allow_html=True)
                for item in data["action_items"]:
                    owner = item["owner_email"] or "unassigned"
                    due = item["due_date"][:10] if item["due_date"] else "no due date"
                    st.markdown(f"☐ **{item['description']}** — {owner}, due `{due}`")
            else:
                st.caption("No action items detected in these notes.")

            st.write("")
            st.markdown(
                '<div class="card-header"><div class="icon icon-orange">📄</div>'
                '<div><div class="eyebrow">MoM Agent · python-docx</div></div></div>',
                unsafe_allow_html=True,
            )
            if st.button("📄  Generate Minutes of Meeting (Word doc)", type="primary"):
                mom_resp = requests.post(f"{API_URL}/mom/{st.session_state['notes_meeting_id']}")
                if mom_resp.status_code == 200:
                    st.session_state["mom_result"] = mom_resp.json()
                else:
                    st.error(f"MoM generation failed: {mom_resp.json().get('detail', mom_resp.text)}")

            if "mom_result" in st.session_state:
                mom_data = st.session_state["mom_result"]
                st.success(f"📄 MoM ready: `{mom_data['mom_path']}`")
                if mom_data.get("stubbed"):
                    st.caption("✉️ Email sending is stubbed — MoM was saved to samples/ instead of emailed.")
    else:
        meeting_id = st.session_state.get("last_meeting_id", 1)

# ---------------------------------------------------------------------------
# TAB 3 — Reminders
# ---------------------------------------------------------------------------
with tab_reminders:
    with st.container(border=True):
        st.markdown(
            f'<div class="card-header"><div class="icon icon-orange">🔔</div>'
            f'<div><div class="eyebrow">Reminder Agent</div>'
            f'<h3 style="margin:0;">Nudge people about meeting #{int(meeting_id)}</h3></div></div>',
            unsafe_allow_html=True,
        )
        st.write("")

        rem_col1, rem_col2 = st.columns(2)

        with rem_col1:
            st.markdown("**Before the meeting**")
            st.caption("Email every participant that it's coming up.")
            if st.button("🔔  Send pre-meeting reminders", type="primary"):
                r = requests.post(f"{API_URL}/reminders/pre-meeting/{int(meeting_id)}")
                if r.status_code == 200:
                    results = r.json()["results"]
                    st.session_state["reminders_sent"] = True
                    st.success(f"Sent {len(results)} reminder(s).")
                    for res in results:
                        st.caption(f"→ `{res['to']}` ({'stubbed' if res['stubbed'] else 'sent'})")
                else:
                    st.error(f"Failed: {r.json().get('detail', r.text)}")

        with rem_col2:
            st.markdown("**After the meeting**")
            st.caption("Chase up anyone with a pending action item.")
            if st.button("✅  Send action-item follow-ups", type="primary"):
                r = requests.post(f"{API_URL}/reminders/follow-up/{int(meeting_id)}")
                if r.status_code == 200:
                    results = r.json()["results"]
                    if results:
                        st.session_state["reminders_sent"] = True
                        st.success(f"Sent {len(results)} follow-up(s).")
                        for res in results:
                            st.caption(f"→ `{res['to']}`: {res['action_item']} ({'stubbed' if res['stubbed'] else 'sent'})")
                    else:
                        st.info("🎉 Nothing pending — everyone's caught up!")
                else:
                    st.error(f"Failed: {r.json().get('detail', r.text)}")

# ---------------------------------------------------------------------------
# TAB 4 — Export
# ---------------------------------------------------------------------------
with tab_export:
    with st.container(border=True):
        st.markdown(
            '<div class="card-header"><div class="icon icon-green">📊</div>'
            '<div><div class="eyebrow">Action-item tracker</div>'
            '<h3 style="margin:0;">Export everything to a spreadsheet</h3></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<p class="helper-text">Every action item across every meeting, ready for Excel or a project tracker.</p>', unsafe_allow_html=True)
        st.write("")

        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            if st.button("⬇️  Download JSON", type="primary"):
                r = requests.get(f"{API_URL}/export/action-items")
                st.download_button(
                    "Save action_items.json",
                    data=r.text,
                    file_name="action_items.json",
                    mime="application/json",
                )
        with exp_col2:
            if st.button("⬇️  Download CSV", type="primary"):
                r = requests.get(f"{API_URL}/export/action-items?format=csv")
                st.download_button(
                    "Save action_items.csv",
                    data=r.text,
                    file_name="action_items.csv",
                    mime="text/csv",
                )
