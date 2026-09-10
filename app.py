import os
import re
import datetime
import streamlit as st
from PIL import Image
from fpdf import FPDF
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

# 1. Environment & Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 2. Page Configuration
st.set_page_config(
    page_title="HealthMate - AI Health & Report Intelligence",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 3. Custom CSS for Professional Card Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #0066cc;
        margin-bottom: 12px;
    }
    .alert-high {
        background-color: #fff5f5;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #e53e3e;
        margin-bottom: 12px;
    }
    .alert-normal {
        background-color: #f0fff4;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #38a169;
        margin-bottom: 12px;
    }
    .alert-diet {
        background-color: #fefcbf;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #d69e2e;
        margin-bottom: 12px;
    }
    .stDownloadButton>button {
        width: 100%;
        background-color: #0066cc;
        color: white;
        font-weight: bold;
        padding: 12px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# 4. Header Banner
st.title("HealthMate 🩺")
st.caption("AI-Powered Clinical Health Assistant - Smart Lab Reports, Medicine Scanner & First-Aid")

# 5. API Key Check
if not api_key:
    st.error("⚠️ GEMINI_API_KEY is missing! Set it in your .env or Streamlit Cloud Secrets.")
    st.stop()

# 6. Gemini Client
try:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(client_args={'verify': False})
    )
except Exception as e:
    st.error(f"Error connecting to AI: {e}")
    st.stop()

CHAT_MODEL = "gemini-3.5-flash-lite"
VISION_MODEL = "gemini-3.6-flash"

# Helper: Clean text for PDF (Removes emojis and non-standard symbols)
def clean_for_pdf(text):
    if not text:
        return ""
    # Strip emojis and keep standard printable ascii/latin1 characters
    clean = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)
    # Remove markdown asterisks and hashtags for clean printout
    clean = clean.replace("**", "").replace("###", "").replace("##", "").replace("#", "")
    return clean

# Helper: Generate Clean Professional HealthMate PDF
def create_healthmate_pdf(report_text, report_type="Clinical Pathology Report"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Top Brand Header
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

    # Meta Info Box
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(50, 50, 50)
    current_date = datetime.datetime.now().strftime("%d %B %Y, %I:%M %p")
    pdf.cell(100, 6, f'Document Type: {report_type}', new_x="RIGHT", new_y="TOP")
    pdf.cell(90, 6, f'Generated On: {current_date}', new_x="LMARGIN", new_y="NEXT", align='R')
    pdf.ln(4)

    # Content Body
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(30, 30, 30)

    cleaned_body = clean_for_pdf(report_text)
    pdf.multi_cell(0, 5.5, cleaned_body)

    # Bottom Footer & Promotional Disclaimer
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

# 7. Sidebar: Tools & Safety Controls
with st.sidebar:
    st.header("⚙️ Health Tools")
    quiz_mode = st.toggle("Health Quiz Mode 🧠", value=False)

    st.markdown("---")
    st.subheader("📊 Quick BMI Calculator")
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

    st.metric(label="Your BMI", value=bmi, delta=bmi_status)

    if st.button("🥗 Ask Diet Plan for My BMI", use_container_width=True):
        st.session_state.bmi_prompt = f"My height is {height_cm}cm, weight is {weight_kg}kg, and BMI is {bmi} ({bmi_status}). Suggest a healthy Indian diet and fitness routine."

    st.markdown("---")
    st.subheader("🚨 Emergency Helpline (India)")
    st.error(
        "🚑 Ambulance: **102 / 108**\n\n"
        "🚨 National Emergency: **112**\n\n"
        "🧠 Mental Health (Tele-MANAS): **14416**"
    )

    st.markdown("---")
    st.markdown("### 🛡️ Medical Disclaimer")
    st.info(
        "HealthMate is an educational tool. "
        "It does not replace professional clinical diagnosis. "
        "Always consult a registered medical doctor."
    )

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_analysis = None
        st.rerun()

# 8. System Prompt
BASE_PROMPT = """
You are HealthMate, an empathetic, highly knowledgeable medical first-aid and clinical wellness assistant.
Role: First-aid advisor, lab report explainer, and wellness guide.
Task: Explain symptoms, first-aid remedies, blood test/lab reports, diet, and healthy lifestyle habits.
Rules:
- Give clear, structured responses with headings and bullet points.
- STRICT INDIAN EMERGENCY PROTOCOL: If symptoms sound severe or life-threatening (e.g. acute chest pain, breathing difficulty, stroke symptoms, heavy bleeding), strictly advise calling 112 (National Emergency) or 108/102 (Ambulance). Never mention 911.
- Say 'I am not sure' if unsure, and redirect off-topic questions back to health.
- End your response with one caring check-in question.
"""

if quiz_mode:
    SYSTEM_INSTRUCTION = (
        BASE_PROMPT
        + "\n\nQUIZ MODE ACTIVE: After your response, ask 1 multiple-choice health question (with options A, B, C, D). Only ask one at a time."
    )
else:
    SYSTEM_INSTRUCTION = BASE_PROMPT

# 9. Memory Setup
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None

# 10. Multimodal Feature: Lab Report & Medicine Scanner
with st.expander("🔬 Scan Lab Report (Blood/Lipid/Sugar) or Medicine Strip", expanded=True):
    st.write("Upload or photograph a **Blood Test Report, Lipid Profile, or Medicine Strip**:")

    scan_type = st.radio(
        "Select Document Type:",
        ["🩸 Blood / Lab Report (Cholesterol, CBC, Sugar, etc.)", "💊 Medicine Strip / Prescription"],
        horizontal=True
    )

    col1, col2 = st.columns(2)
    with col1:
        img_camera = st.camera_input("Take Live Photo")
    with col2:
        img_upload = st.file_uploader("Or Upload Image File", type=["jpg", "jpeg", "png"])

    selected_image = img_camera if img_camera is not None else img_upload

    if selected_image is not None:
        pil_img = Image.open(selected_image)
        pil_img.thumbnail((1600, 1600))
        st.image(pil_img, caption="Uploaded Document", use_container_width=True)

        if st.button("🔍 Run Comprehensive Medical AI Analysis", use_container_width=True, type="primary"):
            with st.spinner("Analyzing laboratory values, reference ranges, and clinical details..."):
                try:
                    if "Blood" in scan_type:
                        vision_prompt = """
You are an expert clinical pathologist and physician assistant.
Analyze this medical/laboratory test report thoroughly. Organize your response into these exact 5 sections:

### 1. Test Overview & Identification
State the test type (e.g. Lipid Profile, Complete Blood Count, Liver Function) and key patient parameters detected.

### 2. High & Elevated Parameters (Needs Immediate Attention)
- For every parameter that is ABOVE normal, list: Parameter Name, Detected Value, Normal Reference Range.
- Explain in simple terms why it is high and what health risk it presents (e.g. risk to arteries, heart, liver).

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
                        vision_prompt = """
You are a pharmacist and medical assistant. Analyze this medicine or prescription image:

### 1. Medicine Name & Salt Composition
Active ingredients, salt name, and strength.

### 2. Primary Clinical Uses
What disease, symptom, or infection this medication treats.

### 3. Important Safety Precautions & Warnings
Contraindications, key side-effects, interactions.

### 4. Dosage & Administration Notice
Strict reminder to only follow the treating doctor's prescribed dosage and timing.
"""
                    res = client.models.generate_content(
                        model=VISION_MODEL,
                        contents=[pil_img, vision_prompt]
                    )
                    st.session_state.last_analysis = res.text
                    st.session_state.messages.append({"role": "model", "content": f"🔬 **Document Analysis Result:**\n\n{res.text}"})

                except Exception as ex:
                    st.error(f"Analysis error: {ex}")

# 11. DISPLAY ANALYSIS IN PROFESSIONAL CARD FORMAT & PDF DOWNLOAD
if st.session_state.last_analysis:
    analysis_text = st.session_state.last_analysis
    st.markdown("---")
    st.subheader("📋 Official HealthMate Clinical Analysis Card")

    # Display in clean separated cards
    sections = re.split(r'###\s+', analysis_text)
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        lines = sec.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        with st.container(border=True):
            if "High" in title or "Elevated" in title or "Attention" in title:
                st.error(f"🚨 **{title}**")
            elif "Normal" in title or "Optimal" in title:
                st.success(f"✅ **{title}**")
            elif "Diet" in title or "Lifestyle" in title:
                st.warning(f"🥗 **{title}**")
            elif "Doctor" in title or "Precautions" in title:
                st.info(f"👨‍⚕️ **{title}**")
            else:
                st.markdown(f"### 📋 {title}")
            
            st.markdown(body)

    # Clean PDF Download Button with HealthMate Branding (Zero Emojis inside PDF)
    pdf_bytes = create_healthmate_pdf(analysis_text, report_type="Clinical Pathology Analysis")

    st.download_button(
        label="📥 Download Official HealthMate Analysis Report (PDF)",
        data=pdf_bytes,
        file_name="HealthMate_Clinical_Report.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.caption("📄 Clean, print-ready PDF without emojis, fully formatted with HealthMate clinical headers.")

# 12. Quick Action Chips
st.write("**⚡ Quick Topics:**")
chip_cols = st.columns(4)
quick_prompt = None

if chip_cols[0].button("🩹 Minor Cut/Burn", use_container_width=True):
    quick_prompt = "Quick first aid steps for a minor burn or cut."
if chip_cols[1].button("🤕 Headache & Fever", use_container_width=True):
    quick_prompt = "Home remedies and first aid for a mild headache and fever."
if chip_cols[2].button("🧘 Stress Relief", use_container_width=True):
    quick_prompt = "Give a 1-minute calming breathing exercise for anxiety."
if chip_cols[3].button("💧 Hydration & Gut", use_container_width=True):
    quick_prompt = "3 essential daily hydration and gut health tips."

# Check if BMI button was clicked
if "bmi_prompt" in st.session_state and st.session_state.bmi_prompt:
    quick_prompt = st.session_state.bmi_prompt
    st.session_state.bmi_prompt = None

# 13. Replay Existing Conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 14. Chat Input and Streaming Generation
user_input = st.chat_input("Ask a health, lab report, or wellness question...")
active_prompt = quick_prompt if quick_prompt else user_input

if active_prompt:
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user"):
        st.markdown(active_prompt)

    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part.from_text(text=m["content"])]
        )
        for m in st.session_state.messages
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
            st.session_state.messages.append({"role": "model", "content": answer})

        except APIError as e:
            if any(code in str(e) for code in ["400", "401", "403"]):
                st.error("⚠️ Invalid Gemini API Key. Please verify in Google AI Studio.")
            elif "429" in str(e):
                st.warning("⏳ Free tier limit reached. Please wait a moment.")
            else:
                st.error(f"AI Service Error: {e}")
        except Exception as e:
            st.error(f"Something went wrong: {e}")