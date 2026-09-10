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

# 2. Page Configuration (Mobile-optimized, fast UI)
st.set_page_config(
    page_title="HealthMate - AI Health & Wellness",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 3. Header Banner
st.title("HealthMate 🩺")
st.caption("Blazing Fast AI Health Companion - First Aid, Medicine Scanner & Wellness")

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

# Ultra-fast model
FAST_MODEL = "gemini-3.5-flash-lite"

# 6. Sidebar: Tools & Safety Controls
with st.sidebar:
    st.header("⚙️ Health Tools")

    # Quiz Mode Toggle
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
        st.session_state.bmi_prompt = f"My height is {height_cm}cm, weight is {weight_kg}kg, and BMI is {bmi} ({bmi_status}). Suggest a quick, healthy meal plan."

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
Rules:
- Keep explanations ultra-crisp, bullet-pointed, and under 120 words.
- Provide 1 practical first-aid or home care step first.
- STRICT INDIAN EMERGENCY PROTOCOL: If symptoms sound severe or life-threatening (e.g. chest pain, breathing trouble, severe bleeding, stroke signs), immediately tell the user to call 112 (National Emergency) or 108/102 (Ambulance) or go to the nearest emergency room. NEVER mention 911 under any circumstances; always use Indian emergency numbers 112 / 108.
- Say 'I am not sure' if unsure, and redirect off-topic questions back to health.
- End with one short caring check-in question.
"""

if quiz_mode:
    SYSTEM_INSTRUCTION = (
        BASE_PROMPT
        + "\n\nQUIZ MODE ACTIVE: After your concise response, ask 1 multiple-choice health question (with options A, B, C, D). Only ask one at a time."
    )
else:
    SYSTEM_INSTRUCTION = BASE_PROMPT

# 8. Memory Setup
if "messages" not in st.session_state:
    st.session_state.messages = []

# 9. Multimodal Feature: Medicine Scanner (with Image Auto-Compression for 10x Speed!)
with st.expander("📸 Scan Medicine Strip or Prescription (Camera / Upload)", expanded=False):
    st.write("Scan a medicine strip or prescription for instant salt, usage, and safety precautions:")
    
    col1, col2 = st.columns(2)
    with col1:
        img_camera = st.camera_input("Take Live Photo")
    with col2:
        img_upload = st.file_uploader("Or Upload Image", type=["jpg", "jpeg", "png"])

    selected_image = img_camera if img_camera is not None else img_upload

    if selected_image is not None:
        pil_img = Image.open(selected_image)
        # SPEED TRICK: Resize/Compress photo to max 800x800 for instant network transfer
        pil_img.thumbnail((800, 800))
        st.image(pil_img, caption="Scanned Image (Optimized)", use_container_width=True)
        
        if st.button("⚡ Quick Scan Medicine", use_container_width=True, type="primary"):
            with st.spinner("Fast-analyzing with AI..."):
                try:
                    vision_prompt = (
                        "Analyze this medicine/prescription photo in under 100 words:\n"
                        "- Medicine Name & Salt\n"
                        "- Primary Use\n"
                        "- Key Safety Caution\n"
                        "- Reminder: Follow doctor prescription only."
                    )
                    res = client.models.generate_content(
                        model=FAST_MODEL,
                        contents=[pil_img, vision_prompt]
                    )
                    st.success("Analysis Complete:")
                    st.markdown(res.text)
                    st.session_state.messages.append({"role": "model", "content": f"📸 **Medicine Scan:**\n\n{res.text}"})
                except Exception as ex:
                    st.error(f"Image scan error: {ex}")

# 10. Quick Action Chips (Instant 1-click solutions)
st.write("**⚡ Quick Topics:**")
chip_cols = st.columns(4)
quick_prompt = None

if chip_cols[0].button("🩹 Minor Cut/Burn", use_container_width=True):
    quick_prompt = "Quick first aid steps for a minor burn or cut."
if chip_cols[1].button("🤕 Headache & Fever", use_container_width=True):
    quick_prompt = "Home remedies for a mild headache and fever."
if chip_cols[2].button("🧘 Stress Relief", use_container_width=True):
    quick_prompt = "Give a 1-minute calming breathing exercise."
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

# 12. Chat Input and Streaming Generation (Zero Delay!)
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
        try:
            # Stream tokens in real time (instant typing effect)
            stream = client.models.generate_content_stream(
                model=FAST_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.6,
                    max_output_tokens=300
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