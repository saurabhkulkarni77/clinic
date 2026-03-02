import streamlit as st
import google.generativeai as genai
import streamlit_authenticator as stauth

# --- 1. Security & Authentication (Retained for Privacy) ---
try:
    credentials = st.secrets["credentials"].to_dict()
    cookie = st.secrets["cookie"].to_dict()
    authenticator = stauth.Authenticate(
        credentials, cookie["name"], cookie["key"], int(cookie["expiry_days"])
    )
except Exception as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

result = authenticator.login('main') if hasattr(authenticator, 'login') else None
authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")

# --- 2. Clinical Assessment Engine (Replacing Security Audit) ---
def run_clinical_audit(report_text):
    """Checks if the AI output includes mandatory clinical safety checks."""
    checks = {
        "Red Flags (Neurological)": any(x in report_text.lower() for x in ["cauda", "numbness", "weakness"]),
        "Subjective Pain Scale": "VAS" in report_text.upper() or "1-10" in report_text,
        "Anatomical Localization": any(x in report_text.lower() for x in ["origin", "insertion", "joint", "nerve"]),
        "Pyrotherapy Contraindications": "heat" in report_text.lower() or "thermal" in report_text.lower(),
        "Special Tests": any(x in report_text.lower() for x in ["test", "maneuver", "sign"])
    }
    return checks

# --- 3. Main App Logic ---
if authentication_status:
    authenticator.logout("Logout", "sidebar")
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.0-flash') # Using the latest Flash model

    st.title("🌡️ Physiotherapy & Pyrotherapy Diagnostic Agent")
    st.markdown("### Clinical Assessment & Treatment Planning")

    # Patient Symptoms Input
    with st.expander("📝 Patient Intake Data", expanded=True):
        symptoms = st.text_area("Describe Patient Symptoms (e.g., L4-L5 radiating pain, sharp, worse at night):")
        history = st.text_input("Relevant Medical History / Previous Injuries:")
        current_heat_tolerance = st.slider("Patient Subjective Heat Tolerance", 1, 10, 5)

    if st.button("Generate Diagnostic Report"):
        if not symptoms:
            st.warning("Please enter patient symptoms.")
        else:
            with st.spinner("Analyzing Anatomy and Physiology..."):
                prompt = f"""
                Act as a Senior Physiotherapist and Pyrotherapy Specialist. 
                Analyze the following patient data:
                Symptoms: {symptoms}
                History: {history}
                Heat Tolerance: {current_heat_tolerance}/10

                Provide a comprehensive report including:
                1. DIAGNOSIS: Differential diagnosis based on anatomy and physiology.
                2. SUBJECTIVE PAIN ASSESSMENT: Analyze the patient's perspective using VAS and descriptors.
                3. PHYSICAL ASSESSMENT: List specific Orthopedic Special Tests to perform.
                4. CLINICAL QUESTIONS: 5 targeted questions to ask the patient to rule out red flags.
                5. PYROTHERAPY PLAN: How to apply heat therapy (duration, intensity, contraindications) specific to this anatomy.
                
                Format the output with clear headings and bullet points.
                """
                
                response = model.generate_content(prompt)
                clinical_report = response.text
                st.session_state.clinical_report = clinical_report

    # --- Display Results ---
    if "clinical_report" in st.session_state:
        report = st.session_state.clinical_report
        
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📋 Clinical Diagnostic Report")
            st.markdown(report)
            st.download_button("💾 Export Clinical Note", data=report, file_name="Patient_Assessment.txt")

        with col2:
            st.subheader("🛡️ Safety & Quality Audit")
            audit = run_clinical_audit(report)
            for check, passed in audit.items():
                st.write(f"{'✅' if passed else '⚠️'} {check}")
            
            st.info("**Disclaimer:** This AI tool is for clinical decision support and does not replace professional medical judgment.")

elif authentication_status == False:
    st.error("Login failed.")
