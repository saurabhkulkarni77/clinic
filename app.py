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

    # ─────────────────────────────────────────
    # PAGE 1: Pain Analysis
    # ─────────────────────────────────────────
    if page == "🩺 Pain Analysis":
        st.title("🩺 Pain Severity & Anatomy Agent")

        severity = st.slider("Select Pain Severity (VAS)", 1, 10, 5)
        location = st.text_input("Anatomical Location")

        if st.button("Analyze"):
            with st.spinner("Analyzing..."):
                response = model.generate_content(
                    f"Analyze pain level {severity} at {location} for anatomy and red flags."
                )
                st.markdown(response.text)
                st.session_state.db.append({
                    "name": "New Patient",
                    "level": severity,
                    "location": location,
                    "date": str(date.today()),
                    "time": "",
                    "phone": "",
                    "status": "Walk-in"
                })

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

            display_data = []
            for entry in st.session_state.db:
                if show_all or entry.get("date") == str(filter_date):
                    display_data.append({
                        "Patient": entry.get("name", "N/A"),
                        "Date": entry.get("date", "N/A"),
                        "Time": entry.get("time", "N/A"),
                        "Area": entry.get("location", "N/A"),
                        "Pain (VAS)": entry.get("level", "N/A"),
                        "Session": entry.get("session", "N/A"),
                        "Therapist": entry.get("therapist", "N/A"),
                        "Status": entry.get("status", "N/A"),
                    })

            if display_data:
                st.dataframe(display_data, use_container_width=True)
                st.caption(f"Total appointments: {len(display_data)}")
            else:
                st.info("No appointments found for the selected date.")

            if st.button("🗑️ Clear All Appointments", type="secondary"):
                st.session_state.db = []
                st.rerun()
        else:
            st.info("No appointments booked yet. Use the **Book Appointment** page to add one.")

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
