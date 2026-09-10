import os
import streamlit as st
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

# 1. Environment and Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 2. Page Configuration
st.set_page_config(
    page_title="HealthMate - AI Health & Lab Report Analyzer",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 3. Header Banner
st.title("HealthMate 🩺")
st.caption("AI Health Companion - Lab Report Reader, Medicine Scanner & First Aid")

# 4. API Key Check
if not api_key:
    st.error("⚠️ GEMINI_API_KEY is missing! Set it in your .env or Streamlit Cloud Secrets.")
    st.stop()

# 5. Gemini Client
try:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(client_args={'verify': False})
    )
except Exception as e:
    st.error(f"Error connecting to AI: {e}")
    st.stop()

# Models
CHAT_MODEL = "gemini-3.5-flash-lite"
VISION_MODEL = "gemini-3.6-flash"

# 6. Sidebar: Tools & Safety Controls
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
        "Always consult a registered medical doctor for prescriptions and emergency treatment."
    )

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 7. System Prompt Configuration
BASE_PROMPT = """
You are HealthMate, an empathetic, highly knowledgeable medical first-aid and clinical wellness assistant.
Role: First-aid advisor, lab report explainer, and wellness guide.
Task: Explain symptoms, first-aid remedies, blood test/lab reports, diet, and healthy lifestyle habits.
Rules:
- Give clear, structured responses with headings and bullet points.
- If the user discusses lab reports or specific health markers (like cholesterol, sugar, BP), explain what the values mean, what is high/low, and give actionable diet/exercise tips.
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

# 8. Memory Setup
if "messages" not in st.session_state:
    st.session_state.messages = []

# 9. Multimodal Feature: Lab Report & Medicine Scanner
with st.expander("🔬 Scan Lab Report (Blood/Urine/Lipid) or Medicine Strip", expanded=True):
    st.write("Upload or photograph a **Blood Test Report, Lipid Profile, Prescription, or Medicine Strip**:")

    scan_type = st.radio(
        "Select Document Type:",
        ["🩸 Blood / Lab Report (Cholesterol, CBC, Sugar, etc.)", "💊 Medicine Strip / Prescription"],
        horizontal=True
    )

    col1, col2 = st.columns(2)
    with col1:
        img_camera = st.camera_input("Take Live Photo with Camera")
    with col2:
        img_upload = st.file_uploader("Or Upload Image File", type=["jpg", "jpeg", "png"])

    selected_image = img_camera if img_camera is not None else img_upload

    if selected_image is not None:
        pil_img = Image.open(selected_image)
        # Keep clear resolution for readable medical text (max 1600x1600)
        pil_img.thumbnail((1600, 1600))
        st.image(pil_img, caption="Uploaded Document", use_container_width=True)

        if st.button("🔍 Run Comprehensive Medical AI Analysis", use_container_width=True, type="primary"):
            with st.spinner("Analyzing laboratory values, reference ranges, and clinical details..."):
                try:
                    if "Blood" in scan_type:
                        vision_prompt = """
You are an expert clinical laboratory pathologist and physician assistant.
Analyze this medical/laboratory test report in thorough, clear detail:

1. 📋 **Report Identification**: What test is this (e.g. Lipid Profile, CBC, HbA1c, Thyroid, etc.)?
2. 🔴 **High / Elevated Parameters**:
   - For every parameter that is ABOVE the normal range, list: Parameter Name, Detected Value, Normal Reference Range.
   - Explain clearly in plain terms what being elevated means for the patient's health.
3. 🟡 **Low / Subnormal Parameters**:
   - List any parameters BELOW normal range and their clinical significance.
4. 🟢 **Normal / Optimal Parameters**:
   - Briefly mention parameters that are safe and normal.
5. 🥗 **Targeted Dietary & Lifestyle Action Plan**:
   - **Foods to Strictly Avoid / Reduce** (e.g., trans fats, deep fried snacks, excess refined sugar, processed meats).
   - **Foods to Include** (e.g., high soluble fiber, oats, garlic, flaxseed, leafy vegetables, hydration).
   - Recommended daily physical activity (e.g., 30 mins brisk walking).
6. 👨‍⚕️ **Questions for Your Doctor**:
   - 2-3 specific questions the patient should ask their treating doctor.
7. 🛡️ **Medical Disclaimer**:
   - Remind the user that this is an AI screening analysis and formal medical treatment/prescriptions require a certified doctor.

Format with clear headers, bullet points, and appropriate status icons.
"""
                    else:
                        vision_prompt = """
You are a pharmacist and medical assistant. Analyze this medicine or prescription image:
1. 💊 **Medicine Name & Salt Composition**: Name, strength, and active pharmaceutical ingredient.
2. 🎯 **Primary Use / Indication**: What condition is this medication commonly prescribed for?
3. ⚠️ **Key Precautions & Warnings**: Important side-effects, interactions (e.g. avoid with alcohol), or contraindications.
4. ⏰ **General Usage Caution**: Strictly emphasize following the doctor's prescribed dosage and timing.

Keep it clear, well-structured, and concise.
"""
                    res = client.models.generate_content(
                        model=VISION_MODEL,
                        contents=[pil_img, vision_prompt]
                    )
                    st.success("Analysis Complete!")
                    st.markdown(res.text)
                    st.session_state.messages.append({"role": "model", "content": f"🔬 **Document Analysis Result:**\n\n{res.text}"})
                except Exception as ex:
                    st.error(f"Analysis error: {ex}")

# 10. Quick Action Chips
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

# 11. Replay Existing Conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 12. Chat Input and Streaming Generation
user_input = st.chat_input("Ask a health, lab report, or wellness question...")
active_prompt = quick_prompt if quick_prompt else user_input

if active_prompt:
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user"):
        st.markdown(active_prompt)

    # Format full history for Gemini
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