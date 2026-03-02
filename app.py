import streamlit as st
import google.generativeai as genai
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

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
    
    # Configure AI
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')

    st.title("🩺 Pain Severity & Anatomy Agent")
    
    # Internal Patient Database (Session State)
    if "db" not in st.session_state:
        st.session_state.db = []

    # UI Logic
    severity = st.slider("Select Pain Severity (VAS)", 1, 10, 5)
        
    location = st.text_input("Anatomical Location")
    
    if st.button("Analyze"):
        with st.spinner("Analyzing..."):
            response = model.generate_content(f"Analyze pain level {severity} at {location} for anatomy and red flags.")
            st.markdown(response.text)
            st.session_state.db.append({"name": "New Patient", "level": severity, "date": "2026-03-01"})

    if st.session_state.db:
        st.subheader("Internal Schedule")
        st.table(st.session_state.db)

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
