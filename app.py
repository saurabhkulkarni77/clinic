import streamlit as st
import google.generativeai as genai
import streamlit_authenticator as stauth
import pandas as pd
from datetime import datetime, time

# --- 1. Session State Initialization ---
if "patient_db" not in st.session_state:
    st.session_state.patient_db = []

# --- 2. Main App Logic ---
if st.session_state.get("authentication_status"):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')

    st.sidebar.title(f"Dr. {st.session_state.name}'s Portal")
    page = st.sidebar.radio("Navigate", ["Clinical Assessment", "Patient Schedule"])

    # --- PAGE 1: CLINICAL ASSESSMENT ---
    if page == "Clinical Assessment":
        st.header("🩺 Anatomical Diagnostic & Pain Assessment")
        
        with st.form("assessment_form"):
            p_name = st.text_input("Patient Name")
            
            # Pain Severity Scale (Replacing Heat Tolerance)
            st.write("### Subjective Pain Severity (VAS)")
            pain_level = st.slider("Select Pain Level (1 = Minimal, 10 = Emergency)", 1, 10, 5)
            
            pain_type = st.multiselect("Pain Quality", 
                ["Sharp/Stabbing", "Dull/Aching", "Burning", "Electrical", "Throbbing"])
            
            symptoms = st.text_area("Anatomical Location & Symptoms (e.g., Left side L5 radiating to lateral calf)")
            
            submitted = st.form_submit_button("Generate Clinical Analysis")
            
            if submitted:
                with st.spinner("Analyzing Pathophysiology..."):
                    # Prompting the AI to focus on Anatomy, Physiology, and Pain Severity
                    prompt = f"""
                    Act as a Senior Physiotherapist. 
                    Patient: {p_name}
                    Pain Severity: {pain_level}/10
                    Pain Quality: {', '.join(pain_type)}
                    Location/Symptoms: {symptoms}

                    Provide a professional assessment based on:
                    1. ANATOMY: Likely structures involved (muscles, nerves, ligaments).
                    2. PHYSIOLOGY: Explain the pain mechanism (e.g., Peripheral sensitization, Ischemia, Nerve Compression).
                    3. CLINICAL TESTS: 3 physical tests to confirm the diagnosis.
                    4. URGENCY: Based on a pain level of {pain_level}, what are the immediate red flags to check for?
                    """
                    response = model.generate_content(prompt)
                    st.session_state.last_assessment = response.text
                    
                    st.session_state.patient_db.append({
                        "Name": p_name,
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Pain Level": f"{pain_level}/10",
                        "Assessment": response.text,
                        "Status": "Evaluated"
                    })

        if "last_assessment" in st.session_state:
            st.markdown("---")
            st.markdown(st.session_state.last_assessment)

    # --- PAGE 2: PATIENT SCHEDULE ---
    elif page == "Patient Schedule":
        st.header("📅 Patient Management")
        
        if st.session_state.patient_db:
            df = pd.DataFrame(st.session_state.patient_db)
            
            # Allow scheduling for evaluated patients
            st.subheader("Schedule Follow-up")
            p_list = [p["Name"] for p in st.session_state.patient_db]
            selected_p = st.selectbox("Select Patient", p_list)
            appt_date = st.date_input("Date")
            appt_time = st.time_input("Time", time(9, 0))
            
            if st.button("Book Appointment"):
                st.success(f"Confirmed: {selected_p} on {appt_date} at {appt_time}")
            
            st.markdown("---")
            st.subheader("Patient Records & Pain History")
            st.dataframe(df[["Name", "Date", "Pain Level", "Status"]])
        else:
            st.info("No assessments recorded yet.")
