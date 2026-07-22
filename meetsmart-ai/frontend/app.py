import streamlit as st
import requests
from datetime import date, timedelta

API_URL = "http://localhost:8000"

st.set_page_config(page_title="MeetSmart AI", page_icon="📅")
st.title("📅 MeetSmart AI — Book a Meeting")

# --- Load employees ---
try:
    employees = requests.get(f"{API_URL}/employees").json()
except requests.exceptions.ConnectionError:
    st.error("Backend not reachable. Start it with `uvicorn app.main:app --reload --port 8000`.")
    st.stop()

email_by_name = {e["name"]: e["email"] for e in employees}

st.subheader("1. Pick participants")
selected_names = st.multiselect("Employees", list(email_by_name.keys()))

st.subheader("2. Pick a date & duration")
meeting_date = st.date_input("Date", value=date.today() + timedelta(days=1))
duration = st.selectbox("Duration (minutes)", [15, 30, 45, 60], index=1)

if st.button("Find available slots", type="primary"):
    if not selected_names:
        st.warning("Pick at least one participant.")
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
    st.subheader("3. Available slots")
    if not slots:
        st.info("No common free slots found for that day.")
    else:
        labels = [f"{s['start_time'][11:16]} – {s['end_time'][11:16]}" for s in slots]
        choice_idx = st.radio("Pick a slot", range(len(labels)), format_func=lambda i: labels[i])

        meeting_title = st.text_input("Meeting title", value="Sync-up")
        agenda = st.text_area("Agenda (optional)", value="")

        if st.button("Confirm booking", type="primary"):
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
                    f"Booked! Meeting #{booking['meeting_id']} — "
                    f"{booking['start_time'][11:16]}–{booking['end_time'][11:16]} "
                    f"with {', '.join(booking['participant_emails'])}"
                )
                if booking.get("ics_path"):
                    st.info(f"📎 .ics invite generated: `{booking['ics_path']}`")
                    if booking.get("invite_stubbed"):
                        st.caption("Email sending is stubbed — invite was saved to samples/ instead of emailed.")
                st.session_state["last_meeting_id"] = booking["meeting_id"]
                del st.session_state["slots"]
            else:
                st.error(f"Booking failed: {resp.json().get('detail', resp.text)}")

st.divider()
st.subheader("4. Meeting notes → structured summary & action items")

default_meeting_id = st.session_state.get("last_meeting_id", 1)
meeting_id = st.number_input("Meeting ID", min_value=1, value=default_meeting_id, step=1)
raw_notes = st.text_area(
    "Paste meeting transcript / raw notes",
    placeholder="e.g. Priya will update the test plan by Friday. Ismail to review PR #42 tomorrow...",
    height=150,
)

if st.button("Generate structured notes"):
    if not raw_notes.strip():
        st.warning("Paste some notes first.")
    else:
        with st.spinner("Notes Agent is structuring this with Groq..."):
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
    st.success("Notes structured.")
    st.markdown(f"**Summary:** {data['summary']}")
    if data["action_items"]:
        st.markdown("**Action items:**")
        for item in data["action_items"]:
            owner = item["owner_email"] or "unassigned"
            due = item["due_date"][:10] if item["due_date"] else "no due date"
            st.markdown(f"- {item['description']} — *{owner}, due {due}*")
    else:
        st.caption("No action items detected.")

    if st.button("📄 Generate Minutes of Meeting (Word doc)"):
        mom_resp = requests.post(f"{API_URL}/mom/{st.session_state['notes_meeting_id']}")
        if mom_resp.status_code == 200:
            st.session_state["mom_result"] = mom_resp.json()
        else:
            st.error(f"MoM generation failed: {mom_resp.json().get('detail', mom_resp.text)}")

    if "mom_result" in st.session_state:
        mom_data = st.session_state["mom_result"]
        st.success(f"MoM generated: `{mom_data['mom_path']}`")
        if mom_data.get("stubbed"):
            st.caption("Email sending is stubbed — MoM was saved to samples/ instead of emailed.")
