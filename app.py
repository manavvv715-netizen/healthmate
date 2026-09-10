import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

# 1. Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 2. Streamlit Page Configuration
st.set_page_config(
    page_title="HealthMate ??",
    page_icon="??",
    layout="centered"
)

# 3. Title & Caption
st.title("HealthMate ??")
st.caption("Your Personal AI Health & Wellness Guide — First Aid, Symptoms & Lifestyle Tips")

# 4. Check API Key
if not api_key:
    st.error("?? GEMINI_API_KEY is missing! Please check your .env file or Streamlit secrets.")
    st.stop()

# 5. Initialize Gemini Client
try:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(client_args={'verify': False})
    )
except Exception as e:
    st.error(f"Error initializing AI client: {e}")
    st.stop()

# 6. Sidebar: Controls & Modes
with st.sidebar:
    st.header("?? HealthMate Controls")
    
    # Mode Toggle (Prompt 3 feature from workshop)
    quiz_mode = st.toggle("Health Quiz Mode ??", value=False)
    
    st.markdown("---")
    st.markdown("### ??? Medical Disclaimer")
    st.info(
        "HealthMate provides wellness information and first-aid education. "
        "It is **not** a replacement for professional medical advice. "
        "In an emergency, please visit a hospital or call an ambulance immediately."
    )
    
    st.markdown("---")
    # Clear Chat Button (Prompt 4 feature)
    if st.button("??? Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 7. System Prompt (Role / Task / Context / Rules)
BASE_PROMPT = """
You are HealthMate, an empathetic, caring health and wellness assistant.
Role: First-aid advisor and wellness companion.
Task: Explain symptoms, first-aid remedies, diet tips, and healthy lifestyle habits in simple English.
Context: User queries about symptoms, general health, stress, hydration, and nutrition.
Rules:
- Keep explanations clear, supportive, and under 150 words.
- Provide one practical first-aid or home care remedy when applicable.
- If symptoms are severe (e.g. chest pain, breathing trouble, high fever), strictly advise seeking immediate medical attention.
- Say 'I'm not sure' if unsure, and redirect off-topic questions back to health.
- Always end your response with one caring check-in question.
"""

if quiz_mode:
    SYSTEM_INSTRUCTION = (
        BASE_PROMPT
        + "\n\nQUIZ MODE ACTIVE: After giving your answer, ask 1 multiple-choice health quiz question (with options A, B, C, D) to test the user's health awareness. Only ask one MCQ at a time."
    )
else:
    SYSTEM_INSTRUCTION = BASE_PROMPT

# 8. Memory (st.session_state.messages)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 9. Replay Old Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 10. Chat Input & Processing
if prompt := st.chat_input("Ask a health, first-aid, or wellness question..."):
    # Add user message to state and display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Build conversation history for Gemini
    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part.from_text(text=m["content"])]
        )
        for m in st.session_state.messages
    ]

    # Generate Gemini response
    with st.chat_message("model"):
        with st.spinner("Analyzing and preparing health advice..."):
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
                st.write(answer)
                st.session_state.messages.append({"role": "model", "content": answer})

            except APIError as e:
                # Prompt 4: Friendly error handling
                if any(code in str(e) for code in ["400", "401", "403"]):
                    st.error("?? Invalid Gemini API Key. Please verify your key in Google AI Studio.")
                elif "429" in str(e):
                    st.warning("? Free tier limit reached. Please wait a moment or try another key.")
                else:
                    st.error(f"AI Service Error: {e}")
            except Exception as e:
                st.error(f"Something went wrong: {e}")
