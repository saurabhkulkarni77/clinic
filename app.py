import streamlit as st
import google.generativeai as genai
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from datetime import date, time, datetime

# --- 1. CRITICAL: Initialize session state first ---
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = None

# --- 2. Load Secrets with Error Handling ---
try:
    credentials = st.secrets["credentials"].to_dict()
    cookie = st.secrets["cookie"].to_dict()
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    st.error(f"❌ Configuration Error: {e}")
    st.info("Ensure your Streamlit Cloud Secrets has: [credentials], [cookie], and GEMINI_API_KEY")
    st.stop()

# --- 3. Authenticator Setup ---
authenticator = stauth.Authenticate(
    credentials,
    cookie['name'],
    cookie['key'],
    cookie['expiry_days']
)

# Render Login Widget
try:
    authenticator.login()
except Exception as e:
    st.error(f"Login Widget Error: {e}")

# --- 4. Main App Routing ---
if st.session_state["authentication_status"]:
    authenticator.logout('Logout', 'sidebar')
    st.sidebar.write(f'Welcome *{st.session_state["name"]}*')

    # --- Sidebar Navigation ---
    page = st.sidebar.radio("📋 Navigation", ["🩺 Pain Analysis", "📅 Book Appointment", "📆 Schedule"])

    # Configure AI
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    # Internal Patient Database (Session State)
    if "db" not in st.session_state:
        st.session_state.db = []
    if "analysis_target" not in st.session_state:
        st.session_state.analysis_target = None

    # ─────────────────────────────────────────
    # Helper: build a rich prompt from patient data
    # ─────────────────────────────────────────
    def build_analysis_prompt(patient: dict) -> str:
        lines = [
            "You are a highly experienced physiotherapist. Perform a comprehensive clinical analysis for the following patient and provide:",
            "1. Anatomical analysis of the pain area",
            "2. Likely diagnoses / differential diagnoses",
            "3. Red flags or urgent referral criteria",
            "4. Recommended physiotherapy treatment plan (exercises, modalities, frequency)",
            "5. Expected prognosis and recovery timeline",
            "6. Any lifestyle or self-management advice",
            "",
            "--- PATIENT PROFILE ---",
            f"Name: {patient.get('name', 'Unknown')}",
        ]
        if patient.get("dob"):
            lines.append(f"Date of Birth: {patient['dob']}")
        if patient.get("gender"):
            lines.append(f"Gender: {patient['gender']}")
        lines += [
            f"Pain Location / Area: {patient.get('location', 'Not specified')}",
            f"Pain Severity (VAS 0–10): {patient.get('level', 'Not specified')}",
        ]
        if patient.get("duration"):
            lines.append(f"Duration of Condition: {patient['duration']}")
        if patient.get("referral"):
            lines.append(f"Referral Source: {patient['referral']}")
        if patient.get("session"):
            lines.append(f"Session Type Requested: {patient['session']}")
        if patient.get("therapist"):
            lines.append(f"Assigned Therapist: {patient['therapist']}")
        if patient.get("notes"):
            lines.append(f"Patient's Additional Notes / Symptoms: {patient['notes']}")
        lines.append(f"Appointment Date: {patient.get('date', 'Not specified')}")
        lines.append(f"Appointment Time: {patient.get('time', 'Not specified')}")
        lines.append("")
        lines.append("Please structure your response with clear headings for each section above.")
        return "\n".join(lines)

    # ─────────────────────────────────────────
    # PAGE 1: Pain Analysis
    # ─────────────────────────────────────────
    if page == "🩺 Pain Analysis":
        st.title("🩺 Pain Severity & Anatomy Agent")

        # If triggered from Schedule page, pre-populate with that patient
        if st.session_state.analysis_target is not None:
            patient = st.session_state.analysis_target
            st.info(f"📋 Analysing booked patient: **{patient.get('name')}** — {patient.get('location')} (VAS {patient.get('level')})")
            if st.button("🔍 Run Full Analysis for This Patient"):
                with st.spinner("Generating comprehensive clinical analysis..."):
                    prompt = build_analysis_prompt(patient)
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
            if st.button("✖ Clear & Start Fresh"):
                st.session_state.analysis_target = None
                st.rerun()
        else:
            severity = st.slider("Select Pain Severity (VAS)", 1, 10, 5)
            location = st.text_input("Anatomical Location")

            if st.button("Analyze"):
                with st.spinner("Analyzing..."):
                    new_patient = {
                        "name": "Walk-in Patient",
                        "level": severity,
                        "location": location,
                        "date": str(date.today()),
                        "time": "",
                        "phone": "",
                        "status": "Walk-in"
                    }
                    prompt = build_analysis_prompt(new_patient)
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                    st.session_state.db.append(new_patient)

    # ─────────────────────────────────────────
    # PAGE 2: Book Appointment
    # ─────────────────────────────────────────
    elif page == "📅 Book Appointment":
        st.title("📅 Book a Physiotherapy Visit")
        st.markdown("Please fill in your details below to schedule an appointment.")

        with st.form("booking_form", clear_on_submit=True):
            st.subheader("👤 Patient Information")
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name *")
                dob = st.date_input("Date of Birth", min_value=date(1900, 1, 1), max_value=date.today())
                phone = st.text_input("Phone Number *")
            with col2:
                last_name = st.text_input("Last Name *")
                email = st.text_input("Email Address")
                gender = st.selectbox("Gender", ["Prefer not to say", "Male", "Female", "Other"])

            st.subheader("🦴 Condition Details")
            col3, col4 = st.columns(2)
            with col3:
                pain_location = st.text_input("Area of Pain / Concern *")
                pain_level = st.slider("Pain Severity (VAS 1–10)", 1, 10, 5)
            with col4:
                condition_duration = st.selectbox("How long have you had this condition?", [
                    "Less than 1 week", "1–2 weeks", "2–4 weeks",
                    "1–3 months", "3–6 months", "More than 6 months"
                ])
                referral = st.selectbox("Referral Source", [
                    "Self-referred", "GP/Doctor referral", "Specialist referral",
                    "Insurance referral", "Word of mouth", "Other"
                ])

            additional_notes = st.text_area("Additional Notes / Symptoms", placeholder="Describe your symptoms in more detail...")

            st.subheader("📆 Appointment Preferences")
            col5, col6 = st.columns(2)
            with col5:
                appt_date = st.date_input("Preferred Date *", min_value=date.today())
                therapist_pref = st.selectbox("Therapist Preference", [
                    "No preference", "Dr. Sarah Mitchell", "Dr. James Okafor", "Dr. Priya Nair"
                ])
            with col6:
                appt_time = st.selectbox("Preferred Time *", [
                    "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM",
                    "11:00 AM", "11:30 AM", "1:00 PM", "1:30 PM",
                    "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM",
                    "4:00 PM", "4:30 PM"
                ])
                session_type = st.selectbox("Session Type", [
                    "Initial Assessment (60 min)",
                    "Follow-up Treatment (45 min)",
                    "Hydrotherapy (45 min)",
                    "Sports Injury Assessment (60 min)",
                    "Post-Surgery Rehabilitation (60 min)"
                ])

            consent = st.checkbox("I consent to the collection and use of my personal health information for treatment purposes. *")

            submitted = st.form_submit_button("✅ Confirm Booking", use_container_width=True)

            if submitted:
                if not first_name or not last_name or not phone or not pain_location:
                    st.error("⚠️ Please fill in all required fields marked with *.")
                elif not consent:
                    st.error("⚠️ You must provide consent to proceed.")
                else:
                    full_name = f"{first_name} {last_name}"
                    booking = {
                        "name": full_name,
                        "dob": str(dob),
                        "gender": gender,
                        "phone": phone,
                        "email": email,
                        "location": pain_location,
                        "level": pain_level,
                        "duration": condition_duration,
                        "referral": referral,
                        "notes": additional_notes,
                        "date": str(appt_date),
                        "time": appt_time,
                        "therapist": therapist_pref,
                        "session": session_type,
                        "status": "Confirmed"
                    }
                    st.session_state.db.append(booking)
                    st.success(f"🎉 Appointment confirmed for **{full_name}** on **{appt_date}** at **{appt_time}**!")
                    st.info(f"📋 Session: {session_type} | Therapist: {therapist_pref}")

    # ─────────────────────────────────────────
    # PAGE 3: Schedule Overview
    # ─────────────────────────────────────────
    elif page == "📆 Schedule":
        st.title("📆 Appointment Schedule")

        if st.session_state.db:
            # Filter controls
            col1, col2 = st.columns(2)
            with col1:
                filter_date = st.date_input("Filter by date (leave today to show all)", value=date.today())
            with col2:
                show_all = st.checkbox("Show all appointments", value=True)

            filtered = [
                e for e in st.session_state.db
                if show_all or e.get("date") == str(filter_date)
            ]

            if filtered:
                st.caption(f"Total appointments: {len(filtered)}")
                for i, entry in enumerate(filtered):
                    with st.expander(
                        f"👤 {entry.get('name', 'N/A')}  |  📅 {entry.get('date', '')}  {entry.get('time', '')}  |  🦴 {entry.get('location', 'N/A')}  |  VAS {entry.get('level', '?')}",
                        expanded=False
                    ):
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.markdown(f"**Gender:** {entry.get('gender', 'N/A')}")
                            st.markdown(f"**DOB:** {entry.get('dob', 'N/A')}")
                            st.markdown(f"**Phone:** {entry.get('phone', 'N/A')}")
                            st.markdown(f"**Email:** {entry.get('email', 'N/A')}")
                        with col_b:
                            st.markdown(f"**Pain Area:** {entry.get('location', 'N/A')}")
                            st.markdown(f"**VAS:** {entry.get('level', 'N/A')}")
                            st.markdown(f"**Duration:** {entry.get('duration', 'N/A')}")
                            st.markdown(f"**Referral:** {entry.get('referral', 'N/A')}")
                        with col_c:
                            st.markdown(f"**Session:** {entry.get('session', 'N/A')}")
                            st.markdown(f"**Therapist:** {entry.get('therapist', 'N/A')}")
                            st.markdown(f"**Status:** {entry.get('status', 'N/A')}")
                        if entry.get("notes"):
                            st.markdown(f"**Notes:** {entry['notes']}")

                        # Inline AI analysis
                        btn_key = f"analyse_{i}"
                        result_key = f"result_{i}"
                        if result_key not in st.session_state:
                            st.session_state[result_key] = None

                        col_btn1, col_btn2 = st.columns([2, 1])
                        with col_btn1:
                            if st.button(f"🧠 Run AI Clinical Analysis", key=btn_key):
                                with st.spinner("Generating clinical analysis using all patient data..."):
                                    prompt = build_analysis_prompt(entry)
                                    response = model.generate_content(prompt)
                                    st.session_state[result_key] = response.text
                        with col_btn2:
                            if st.button("📤 Open in Analysis Page", key=f"open_{i}"):
                                st.session_state.analysis_target = entry
                                st.rerun()

                        if st.session_state[result_key]:
                            st.divider()
                            st.markdown("#### 🧠 AI Clinical Analysis")
                            st.markdown(st.session_state[result_key])
            else:
                st.info("No appointments found for the selected date.")

            st.divider()
            if st.button("🗑️ Clear All Appointments", type="secondary"):
                st.session_state.db = []
                st.rerun()
        else:
            st.info("No appointments booked yet. Use the **Book Appointment** page to add one.")

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
