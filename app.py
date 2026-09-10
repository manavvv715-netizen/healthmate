import os
import re
import urllib.parse
import datetime
import streamlit as st
from PIL import Image
from fpdf import FPDF
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

# 1. Environment & Key Setup
load_dotenv()
env_api_key = os.getenv("GEMINI_API_KEY", "")
backup_key = st.sidebar.text_input("🔑 Backup API Key (Optional)", type="password", help="If primary key hits limit, paste a fresh key here.")
api_key = backup_key if backup_key.strip() else env_api_key

# 2. Page Configuration
st.set_page_config(
    page_title="HealthMate AI - Clinical Health Intelligence",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 3. Custom CSS for Modern Hospital-Grade UI Cards
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 14px;
        border-left: 5px solid #0066cc;
        margin-bottom: 10px;
    }
    .stDownloadButton>button {
        width: 100%;
        background-color: #0066cc !important;
        color: white !important;
        font-weight: bold;
        padding: 10px;
        border-radius: 8px;
    }
    .chat-session-btn {
        text-align: left;
        margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)

# 4. API Key Verification
if not api_key:
    st.error("⚠️ GEMINI_API_KEY is missing! Set it in your .env or Streamlit Cloud Secrets.")
    st.stop()

# 5. Initialize Gemini Client
try:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(client_args={'verify': False})
    )
except Exception as e:
    st.error(f"Error connecting to AI: {e}")
    st.stop()

CHAT_MODEL = "gemini-3.5-flash-lite"
# Models with high quota (1,500/day instead of 20/day)
VISION_MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]

def call_gemini_with_fallback(client, contents, system_instruction=None, is_vision=False):
    models = VISION_MODELS if is_vision else [CHAT_MODEL, "gemini-3.5-flash"]
    last_error = None
    for model_name in models:
        try:
            config = types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.5) if system_instruction else None
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
        except Exception as e:
            last_error = e
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                continue
            else:
                raise e
    raise last_error

# Helper: Clean text for PDF (Guarantees Zero Emojis or weird symbols)
def clean_for_pdf(text):
    if not text:
        return ""
    clean = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)
    clean = clean.replace("**", "").replace("###", "").replace("##", "").replace("#", "")
    return clean

# Helper: PDF Generation
def create_healthmate_pdf(report_text, report_type="Clinical Pathology Analysis"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(18, 65, 120)
    pdf.cell(0, 10, 'HEALTHMATE AI CLINICAL INTELLIGENCE', new_x="LMARGIN", new_y="NEXT", align='C')

    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 5, 'Empowering Patients with Precision AI Healthcare Analysis', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 5, 'Web: healthmate-ai.streamlit.app | Powered by Google Gemini', new_x="LMARGIN", new_y="NEXT", align='C')

    pdf.set_draw_color(18, 65, 120)
    pdf.set_line_width(0.6)
    pdf.line(10, 33, 200, 33)
    pdf.ln(8)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(50, 50, 50)
    current_date = datetime.datetime.now().strftime("%d %B %Y, %I:%M %p")
    pdf.cell(100, 6, f'Document Type: {report_type}', new_x="RIGHT", new_y="TOP")
    pdf.cell(90, 6, f'Generated On: {current_date}', new_x="LMARGIN", new_y="NEXT", align='R')
    pdf.ln(4)

    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(30, 30, 30)

    cleaned_body = clean_for_pdf(report_text)
    pdf.multi_cell(0, 5.5, cleaned_body)

    pdf.ln(6)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(
        0, 4,
        "About HealthMate: HealthMate is an advanced AI assistant designed to help patients understand complex laboratory "
        "reports and medicine safety. This document is for educational reference. It is strictly recommended to present "
        "these findings to a certified physician for medical diagnosis and clinical treatment.\n"
        "(c) 2026 HealthMate AI Technologies. All rights reserved."
    )
    return bytes(pdf.output())

# 6. Session State Management (ChatGPT-Style Multi-Chat History)
if "sessions" not in st.session_state:
    # Initialize with Session 1
    init_id = "Session 1"
    st.session_state.sessions = {
        init_id: {
            "title": "General Health Consultation",
            "messages": [],
            "last_analysis": None
        }
    }
    st.session_state.current_session_id = init_id

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = list(st.session_state.sessions.keys())[0]

curr_session = st.session_state.sessions[st.session_state.current_session_id]

# 7. Sidebar: Sessions, Language & Health Tools
with st.sidebar:
    st.title("HealthMate 🩺")

    # New Chat Button
    if st.button("➕ New Consultation", use_container_width=True, type="primary"):
        new_idx = len(st.session_state.sessions) + 1
        new_id = f"Session {new_idx}"
        st.session_state.sessions[new_id] = {
            "title": f"Consultation #{new_idx}",
            "messages": [],
            "last_analysis": None,
            "doctor_note": None
        }
        st.session_state.current_session_id = new_id
        st.session_state.doctor_note = None
        st.session_state.triggered_prompt = None
        st.rerun()

    # Multi-Language Selector (Indian Accessibility Feature)
    selected_lang = st.selectbox(
        "🌐 Consultation Language:",
        ["English", "हिन्दी (Hindi)", "ગુજરાતી (Gujarati)", "Hinglish"],
        index=0
    )

    st.markdown("---")
    st.subheader("💬 Past Consultations")
    for s_id, s_data in list(st.session_state.sessions.items()):
        is_active = (s_id == st.session_state.current_session_id)
        prefix = "👉 " if is_active else "💬 "
        if st.button(f"{prefix}{s_data['title']}", key=f"btn_{s_id}", use_container_width=True):
            st.session_state.current_session_id = s_id
            st.session_state.doctor_note = s_data.get("doctor_note", None)
            st.session_state.triggered_prompt = None
            st.rerun()

    st.markdown("---")
    st.subheader("📊 Interactive BMI Calculator")
    height_cm = st.slider("Height (cm)", min_value=120, max_value=220, value=170)
    weight_kg = st.slider("Weight (kg)", min_value=30, max_value=150, value=65)

    bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)
    if bmi < 18.5:
        bmi_status = "Underweight 🟡"
    elif 18.5 <= bmi < 24.9:
        bmi_status = "Normal weight 🟢"
    elif 25 <= bmi < 29.9:
        bmi_status = "Overweight 🟠"
    else:
        bmi_status = "Obese 🔴"

    st.metric(label="Your BMI Score", value=bmi, delta=bmi_status)

    if st.button("🥗 Get Diet Plan for My BMI", use_container_width=True):
        st.session_state.triggered_prompt = f"My height is {height_cm}cm, weight is {weight_kg}kg, and BMI is {bmi} ({bmi_status}). Suggest a healthy Indian diet and fitness routine."

    st.markdown("---")
    quiz_mode = st.toggle("Health Quiz Mode 🧠", value=False)

    st.markdown("---")
    st.subheader("🚨 My Emergency Contacts")
    st.caption("Apne family/doctor ka number daalo — emergency mein WhatsApp SOS jaayega inhe:")

    sos_name1 = st.text_input("Contact 1 Name", placeholder="e.g. Mummy / Papa", key="sos_name1")
    sos_num1 = st.text_input("Contact 1 WhatsApp Number (+91)", placeholder="e.g. 9876543210", key="sos_num1")

    sos_name2 = st.text_input("Contact 2 Name", placeholder="e.g. Dr. Sharma", key="sos_name2")
    sos_num2 = st.text_input("Contact 2 WhatsApp Number (+91)", placeholder="e.g. 9123456789", key="sos_num2")

    st.markdown("---")
    st.subheader("🚨 National Helpline (India)")
    st.error(
        "🚑 Ambulance: **102 / 108**\n\n"
        "🚨 National Emergency: **112**\n\n"
        "🧠 Mental Health (Tele-MANAS): **14416**"
    )

    st.markdown("---")
    if st.button("🗑️ Clear This Chat", use_container_width=True):
        curr_session["messages"] = []
        curr_session["last_analysis"] = None
        st.rerun()

# 8. Dynamic System Prompt with Language Injection
LANG_INSTRUCTION = f"Respond primarily in {selected_lang}. Ensure medical guidance is culturally relevant for Indian patients."

BASE_PROMPT = f"""
You are HealthMate, an empathetic, clinical health and wellness AI assistant.
Language Rule: {LANG_INSTRUCTION}
Role: First-aid advisor, lab report explainer, triage specialist, and wellness companion.
Task: Explain symptoms, blood test/lab reports, diet, and healthy lifestyle habits.
Rules:
- Keep explanations clear, structured, and easy to understand.
- STRICT INDIAN EMERGENCY PROTOCOL: If symptoms sound severe (chest pain, breathlessness, stroke signs, severe hemorrhage), strictly advise calling 112 (National Emergency) or 108/102 (Ambulance). NEVER mention 911 under any circumstances.
- Say 'I am not sure' if unsure, and redirect off-topic questions back to health.
- Always end with a caring follow-up question.
"""

if quiz_mode:
    SYSTEM_INSTRUCTION = (
        BASE_PROMPT
        + "\n\nQUIZ MODE ACTIVE: After your response, ask 1 multiple-choice health quiz question (options A, B, C, D) in the chosen language."
    )
else:
    SYSTEM_INSTRUCTION = BASE_PROMPT

# 9. Main Header
st.title("HealthMate 🩺")
st.caption(f"Active Consultation: **{curr_session['title']}** | Language: **{selected_lang}**")

# EMERGENCY SOS TOP BANNER (styled card)
with st.container(border=True):
    st.markdown(
        "<div style='background-color:#ffe6e6;padding:12px;border-radius:8px;'><strong>🔴 Feeling severe distress or medical emergency?</strong></div>",
        unsafe_allow_html=True
    )
    sos_col1, sos_col2 = st.columns([3, 1])
    with sos_col1:
        st.empty()
    with sos_col2:
        trigger_sos = st.button("🚨 TRIGGER EMERGENCY SOS", type="primary", use_container_width=True)

# Helper function to generate clean WhatsApp SOS URL
def get_whatsapp_sos_url(phone_num, message_body):
    clean_phone = re.sub(r"[^\d]", "", phone_num)
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
    encoded_msg = urllib.parse.quote(message_body)
    return f"https://api.whatsapp.com/send?phone={clean_phone}&text={encoded_msg}"

# 10. OUT-OF-THE-BOX FEATURE 1: Interactive Visual Body Triage
st.markdown("### 🧍‍♂️ Visual Symptom Triage (Where does it hurt?)")
st.write("Click on a body zone for instant targeted clinical triage:")

triage_cols = st.columns(4)
triage_prompt = None

if triage_cols[0].button("🧠 Head / Migraine", use_container_width=True):
    triage_prompt = "I have a headache and head heaviness. Differentiate between tension headache and migraine, and suggest safe immediate relief."
if triage_cols[1].button("🫀 Chest / Discomfort", use_container_width=True):
    triage_prompt = "I feel discomfort in my chest. Explain the difference between acidity/heartburn vs cardiac chest pain, and emergency warning signs."
if triage_cols[2].button("🫄 Stomach / Digestion", use_container_width=True):
    triage_prompt = "I have stomach cramps and bloating after eating. What home care and diet precautions should I follow right now?"
if triage_cols[3].button("🦵 Joints / Muscle Sprain", use_container_width=True):
    triage_prompt = "I twisted my ankle/leg and have swelling. Explain the standard RICE first-aid method step-by-step."

# 11. OUT-OF-THE-BOX FEATURE 2: Drug-Drug & Food Interaction Checker
with st.expander("⚠️ Drug-Drug & Food Interaction Conflict Checker", expanded=False):
    st.write("Check if two medicines or a food item can dangerously interact when taken together:")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        med1 = st.text_input("First Medicine / Supplement (e.g. Disprin, Paracetamol, Thyronorm)", key="med1_input")
    with col_d2:
        med2 = st.text_input("Second Medicine or Food/Drink (e.g. Ibuprofen, Blood Thinner, Milk, Chai)", key="med2_input")

    if st.button("⚡ Check Drug & Food Safety Conflict", type="primary", use_container_width=True):
        if med1 and med2:
            conflict_query = (
                f"Clinical Drug Interaction Check: Can a patient take '{med1}' together with '{med2}'? "
                "Analyze:\n"
                "1. Safety Status: [🔴 High Risk Conflict / 🟡 Moderate Caution / 🟢 Safe to Combine]\n"
                "2. Mechanism: Why do they interact or interfere?\n"
                "3. Safe Timing: How many hours gap should be kept, or should combination be completely avoided?\n"
                "4. Indian dietary precaution (e.g. taking with water vs milk vs empty stomach)."
            )
            with st.spinner("Screening clinical pharmacology interactions..."):
                try:
                    conflict_res = client.models.generate_content(
                        model=CHAT_MODEL,
                        contents=conflict_query,
                        config=types.GenerateContentConfig(
                            system_instruction=BASE_PROMPT,
                            temperature=0.4
                        )
                    )
                    st.markdown(conflict_res.text)
                    curr_session["messages"].append({"role": "user", "content": f"⚠️ Interaction Check: {med1} + {med2}"})
                    curr_session["messages"].append({"role": "model", "content": conflict_res.text})
                except Exception as ex:
                    st.error(f"Interaction check error: {ex}")
        else:
            st.warning("Please enter both medicine/food names to run the interaction check.")

# 12. Multimodal Lab Report & Medicine Scanner
with st.expander("🔬 Scan Lab Report (Blood/Lipid/Sugar) or Medicine Strip", expanded=False):
    st.write("Upload or photograph a **Blood Test Report, Lipid Profile, or Medicine Strip**:")

    scan_type = st.radio(
        "Select Document Type:",
        ["🩸 Blood / Lab Report (Cholesterol, CBC, Sugar, etc.)", "💊 Medicine Strip / Prescription"],
        horizontal=True
    )

    col1, col2 = st.columns(2)
    sess_key = st.session_state.current_session_id
    with col1:
        img_camera = st.camera_input("Take Live Photo", key=f"cam_{sess_key}")
    with col2:
        img_upload = st.file_uploader("Or Upload Image File", type=["jpg", "jpeg", "png"], key=f"upload_{sess_key}")

    selected_image = img_camera if img_camera is not None else img_upload

    if selected_image is not None:
        pil_img = Image.open(selected_image)
        pil_img.thumbnail((1600, 1600))
        st.image(pil_img, caption="Uploaded Document", use_container_width=True)

        if st.button("🔍 Run Comprehensive Medical AI Analysis", use_container_width=True, type="primary"):
            with st.spinner("Analyzing laboratory values, reference ranges, and clinical details..."):
                try:
                    if "Blood" in scan_type:
                        vision_prompt = f"""
You are an expert clinical pathologist. Language: {selected_lang}.
Analyze this laboratory report thoroughly. Organize your response into these exact 5 sections:

### 1. Test Overview & Identification
State the test type (e.g. Lipid Profile, Complete Blood Count, Liver Function) and key patient parameters detected.

### 2. High & Elevated Parameters (Needs Immediate Attention)
- For every parameter that is ABOVE normal, list: Parameter Name, Detected Value, Normal Reference Range.
- Explain in simple terms why it is high and what health risk it presents.

### 3. Normal & Optimal Parameters
- List parameters that are safely within reference ranges.

### 4. Targeted Diet & Lifestyle Action Plan
- Foods to Strictly Avoid / Reduce (trans fats, deep fried snacks, excess sugar, butter/palm oil).
- Foods to Actively Include (high soluble fiber, oats, garlic, methi seeds, leafy greens, adequate water).
- Exercise recommendation (e.g. 30 mins brisk walking).

### 5. Key Questions for Your Doctor
- 2-3 specific questions the patient should ask their treating doctor during follow-up.
"""
                    else:
                        vision_prompt = f"""
You are a clinical pharmacist. Language: {selected_lang}. Analyze this medicine image:

### 1. Medicine Name & Salt Composition
Active ingredients, salt name, and strength.

### 2. Primary Clinical Uses
What disease, symptom, or infection this medication treats.

### 3. Important Safety Precautions & Warnings
Contraindications, key side-effects, food interactions.

### 4. Dosage & Administration Notice
Strict reminder to only follow the treating doctor's prescribed dosage and timing.
"""
                    res = call_gemini_with_fallback(
                        client=client,
                        contents=[pil_img, vision_prompt],
                        is_vision=True
                    )
                    curr_session["last_analysis"] = res.text
                    curr_session["messages"].append({"role": "model", "content": f"🔬 **Document Analysis Result:**\n\n{res.text}"})

                    # Auto-update session title based on test
                    curr_session["title"] = "Lab Report Analysis"

                except Exception as ex:
                    st.error(f"Analysis error: {ex}")

# 13. Display Clinical Cards & Clean PDF Download
if curr_session["last_analysis"]:
    analysis_text = curr_session["last_analysis"]
    st.markdown("---")
    st.subheader("📋 Official HealthMate Clinical Analysis Card")

    sections = re.split(r'###\s+', analysis_text)
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        lines = sec.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        with st.container(border=True):
            if any(w in title for w in ["High", "Elevated", "Attention"]):
                st.error(f"🚨 **{title}**")
            elif any(w in title for w in ["Normal", "Optimal"]):
                st.success(f"✅ **{title}**")
            elif any(w in title for w in ["Diet", "Lifestyle"]):
                st.warning(f"🥗 **{title}**")
            elif any(w in title for w in ["Doctor", "Precautions"]):
                st.info(f"👨‍⚕️ **{title}**")
            else:
                st.markdown(f"### 📋 {title}")
            st.markdown(body)

    # Clean PDF Download Button (Zero Emojis inside PDF)
    pdf_bytes = create_healthmate_pdf(analysis_text, report_type="Clinical Pathology Analysis")
    st.download_button(
        label="📥 Download Official HealthMate Analysis Report (PDF)",
        data=pdf_bytes,
        file_name="HealthMate_Clinical_Report.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.caption("📄 Clean, print-ready PDF without emojis, fully formatted with HealthMate clinical headers.")

# 14. OUT-OF-THE-BOX FEATURE 3: Doctor Handover Note & WhatsApp Share
st.markdown("---")
col_note1, col_note2 = st.columns([3, 1])
with col_note1:
    st.write("**👨‍⚕️ Preparing to visit a Doctor?** Generate a concise clinical summary note to share on WhatsApp:")
with col_note2:
    if st.button("📋 Generate Doctor Handover Note", use_container_width=True):
        if curr_session["messages"]:
            summary_prompt = (
                "Summarize this patient conversation into a concise 'Doctor Clinical Handover Note':\n"
                "- Chief Complaints & Duration\n"
                "- Key Lab Findings or Medicines Discussed\n"
                "- Vitals/BMI (if mentioned)\n"
                "- Questions to ask the Doctor\n"
                "Format cleanly as bullet points for quick physician reading."
            )
            all_msgs = [f"{m['role']}: {m['content']}" for m in curr_session["messages"][-6:]]
            note_res = client.models.generate_content(
                model=CHAT_MODEL,
                contents="\n".join(all_msgs) + "\n\n" + summary_prompt
            )
            st.session_state.doctor_note = note_res.text
            curr_session["doctor_note"] = note_res.text
        else:
            st.warning("Please chat or analyze a report first so a handover note can be generated.")

if "doctor_note" in st.session_state and st.session_state.doctor_note:
    with st.container(border=True):
        st.markdown("#### 🩺 Doctor Pre-Consultation Summary Note")
        st.markdown(st.session_state.doctor_note)
        encoded_text = urllib.parse.quote(st.session_state.doctor_note)
        wa_url = f"https://api.whatsapp.com/send?text={encoded_text}"
        st.markdown(
            f'<a href="{wa_url}" target="_blank" style="display:inline-block; background-color:#25D366; color:white; padding:8px 16px; border-radius:6px; text-decoration:none; font-weight:bold;">📲 Share with Doctor on WhatsApp</a>',
            unsafe_allow_html=True
        )

# 16. Chat Input (defined early so emergency keyword check can use it)
user_input = st.chat_input("Ask a health, lab report, or wellness question...")

active_prompt = None
if "triggered_prompt" in st.session_state and st.session_state.triggered_prompt:
    active_prompt = st.session_state.triggered_prompt
    st.session_state.triggered_prompt = None
elif triage_prompt:
    active_prompt = triage_prompt
elif user_input:
    active_prompt = user_input

# Check if emergency is triggered either by button or user keywords
is_emergency_triggered = False
emergency_reason = "Critical medical distress reported by user"

if trigger_sos:
    is_emergency_triggered = True

if active_prompt:
    emergency_keywords = ["emergency", "sos", "heart attack", "chest pain", "fainted", "choking", "accident", "bleeding heavily", "bachao", "save me", "can't breathe", "help me", "dard", "takleef", "unconscious", "behosh"]
    if any(kw in active_prompt.lower() for kw in emergency_keywords):
        is_emergency_triggered = True
        emergency_reason = active_prompt

if is_emergency_triggered:
    with st.container(border=True):
        st.error("🚨 **CRITICAL MEDICAL EMERGENCY DETECTED!**")
        st.markdown(
            "HealthMate has activated the **Emergency SOS Dispatch**. "
            "Please remain calm, sit down, keep doors unlocked for first responders, and immediately notify your emergency contacts below:"
        )

        now_str = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
        sos_message = (
            "🚨 *URGENT MEDICAL SOS ALERT via HealthMate AI*\n\n"
            f"⚠️ *Situation:* {emergency_reason}\n"
            f"⏰ *Time:* {now_str}\n"
            "📍 *Status:* Patient requires immediate medical assistance / family presence.\n\n"
            "📞 *Emergency Services:* Dial 112 (National Emergency) or 108 (Ambulance) immediately!\n"
            "— Sent via HealthMate Personal Safety System"
        )

        # Contact 1 WhatsApp Button
        col_wa1, col_wa2, col_call = st.columns(3)
        c1_name = st.session_state.get("sos_name1", "Contact 1")
        c1_num = st.session_state.get("sos_num1", "")
        if c1_num:
            wa_url_1 = get_whatsapp_sos_url(c1_num, sos_message)
            with col_wa1:
                st.markdown(
                    f'<a href="{wa_url_1}" target="_blank" style="display:block; text-align:center; background-color:#25D366; color:white; padding:10px; border-radius:8px; text-decoration:none; font-weight:bold;">📲 WhatsApp SOS: {c1_name}</a>',
                    unsafe_allow_html=True
                )

        # Contact 2 WhatsApp Button
        c2_name = st.session_state.get("sos_name2", "Contact 2")
        c2_num = st.session_state.get("sos_num2", "")
        if c2_num:
            wa_url_2 = get_whatsapp_sos_url(c2_num, sos_message)
            with col_wa2:
                st.markdown(
                    f'<a href="{wa_url_2}" target="_blank" style="display:block; text-align:center; background-color:#25D366; color:white; padding:10px; border-radius:8px; text-decoration:none; font-weight:bold;">📲 WhatsApp SOS: {c2_name}</a>',
                    unsafe_allow_html=True
                )

        with col_call:
            st.markdown(
                '<a href="tel:112" style="display:block; text-align:center; background-color:#e53e3e; color:white; padding:10px; border-radius:8px; text-decoration:none; font-weight:bold;">📞 Call 112 (Ambulance)</a>',
                unsafe_allow_html=True
            )

# 15. Replay Existing Messages
st.markdown("---")
st.subheader("💬 Active Consultation Chat")
for msg in curr_session["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if active_prompt:
    # Auto title first message
    if len(curr_session["messages"]) == 0:
        curr_session["title"] = active_prompt[:25] + "..."

    curr_session["messages"].append({"role": "user", "content": active_prompt})
    with st.chat_message("user"):
        st.markdown(active_prompt)

    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part.from_text(text=m["content"])]
        )
        for m in curr_session["messages"]
    ]

    with st.chat_message("model"):
        try:
            stream = client.models.generate_content_stream(
                model=CHAT_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.6,
                    max_output_tokens=600
                )
            )

            def response_generator():
                for chunk in stream:
                    if chunk.text:
                        yield chunk.text

            answer = st.write_stream(response_generator())
            curr_session["messages"].append({"role": "model", "content": answer})

        except APIError as e:
            if any(code in str(e) for code in ["400", "401", "403"]):
                st.error("⚠️ Invalid Gemini API Key. Please verify in Google AI Studio.")
            elif "429" in str(e):
                st.warning("⏳ Free tier limit reached. Please wait a moment.")
            else:
                st.error(f"AI Service Error: {e}")
        except Exception as e:
            st.error(f"Something went wrong: {e}")