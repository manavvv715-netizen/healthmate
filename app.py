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

# 2. Page Configuration (Mobile-friendly, premium title)
st.set_page_config(
    page_title="HealthMate - AI Health & Wellness",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 3. Header Banner
st.title("HealthMate 🩺")
st.caption("AI-Powered Health Assistant - First Aid, Medicine Scanner & Wellness Guide")

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

# 6. Sidebar: Tools & Safety Controls
with st.sidebar:
    st.header("⚙️ Health Tools")

    # Quiz Mode Toggle (from workshop)
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
        st.session_state.bmi_prompt = f"My height is {height_cm}cm, weight is {weight_kg}kg, and BMI is {bmi} ({bmi_status}). Suggest a healthy, balanced daily meal and hydration plan."

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
        "HealthMate is for educational & first-aid reference only. "
        "In a real emergency, please consult a certified doctor immediately."
    )

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 7. System Prompt Configuration
BASE_PROMPT = """
You are HealthMate, an empathetic, caring medical first-aid and wellness assistant.
Role: First-aid advisor, wellness guide, and health educator.
Task: Explain symptoms, first-aid remedies, diet tips, and healthy lifestyle habits in simple English.
Context: User health queries, first aid, medicine queries, stress, hydration, and nutrition.
Rules:
- Keep explanations clear, supportive, and under 150 words.
- Provide practical, safe home care or first-aid steps when applicable.
- If symptoms are severe (e.g. chest pain, breathing difficulty, severe burns, sudden numbness), strictly advise immediate emergency medical care.
- Say 'I am not sure' if unsure, and keep answers grounded in safe health practices.
- End your response with one caring check-in question.
"""

if quiz_mode:
    SYSTEM_INSTRUCTION = (
        BASE_PROMPT
        + "\n\nQUIZ MODE ACTIVE: After your concise response, ask 1 multiple-choice health question (with options A, B, C, D) to test the user. Ask only one question at a time."
    )
else:
    SYSTEM_INSTRUCTION = BASE_PROMPT

# 8. Memory Setup
if "messages" not in st.session_state:
    st.session_state.messages = []

# 9. Multimodal Feature: Medicine & Prescription Scanner (Judges Showstopper!)
with st.expander("📸 Scan Medicine Strip or Prescription (Camera / Upload)", expanded=False):
    st.write("Take a photo of a medicine strip or prescription to get instant usage, salt details, and precautions:")
    
    col1, col2 = st.columns(2)
    with col1:
        img_camera = st.camera_input("Take Live Photo with Phone Camera")
    with col2:
        img_upload = st.file_uploader("Or Upload Image File", type=["jpg", "jpeg", "png"])

    selected_image = img_camera if img_camera is not None else img_upload

    if selected_image is not None:
        pil_img = Image.open(selected_image)
        st.image(pil_img, caption="Scanned Image", use_container_width=True)
        
        if st.button("🔍 Analyze Medicine with AI", use_container_width=True, type="primary"):
            with st.spinner("Analyzing medicine name, dosage purpose, and safety precautions..."):
                try:
                    vision_prompt = (
                        "Analyze this medicine or prescription image. Provide:\n"
                        "1. Identified Medicine Name & Salt (if clearly visible)\n"
                        "2. Common Uses / Indications\n"
                        "3. General Precautions & Safety Warnings\n"
                        "4. Strictly remind the user to follow their doctor's prescribed dosage.\n"
                        "Keep it concise, well-structured with bullet points."
                    )
                    res = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=[pil_img, vision_prompt]
                    )
                    st.success("Analysis Complete:")
                    st.markdown(res.text)
                    st.session_state.messages.append({"role": "model", "content": f"📸 **Medicine Scanner Result:**\n\n{res.text}"})
                except Exception as ex:
                    st.error(f"Image analysis error: {ex}")

# 10. Quick Action Chips (Fast 1-click demos)
st.write("**⚡ Quick Topics:**")
chip_cols = st.columns(4)
quick_prompt = None

if chip_cols[0].button("🩹 Minor Cut/Burn", use_container_width=True):
    quick_prompt = "How should I treat a minor burn or cut immediately with first aid?"
if chip_cols[1].button("🤕 Headache & Fever", use_container_width=True):
    quick_prompt = "I have a headache and slight body warmth. What home care can help?"
if chip_cols[2].button("🧘 Stress Relief", use_container_width=True):
    quick_prompt = "Guide me through a quick 2-minute breathing exercise to reduce anxiety and stress."
if chip_cols[3].button("💧 Hydration & Diet", use_container_width=True):
    quick_prompt = "What are 4 essential daily habits for good hydration and gut health?"

# Check if BMI button was clicked from sidebar
if "bmi_prompt" in st.session_state and st.session_state.bmi_prompt:
    quick_prompt = st.session_state.bmi_prompt
    st.session_state.bmi_prompt = None

# 11. Replay Existing Conversation
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 12. Chat Input and Generation Logic
user_input = st.chat_input("Ask a health, first-aid, or wellness question...")
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
        with st.spinner("Preparing medical guidance..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.7
                    )
                )
                answer = response.text
                st.markdown(answer)
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