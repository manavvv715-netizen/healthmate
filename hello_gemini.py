import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

key = os.getenv("GEMINI_API_KEY")
client = genai.Client(
    api_key=key,
    http_options=types.HttpOptions(client_args={'verify': False})
)

try:
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Say hello in one short sentence!",
    )
    print("SUCCESS: " + response.text)
except Exception as e:
    print("ERROR:", e)
