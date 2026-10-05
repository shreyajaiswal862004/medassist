import os
from dotenv import load_dotenv
load_dotenv()

print("=" * 40)
groq_key = os.getenv("GROQ_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")
print("GROQ:", groq_key[:10] + "..." if groq_key else "MISSING")
print("GEMINI:", gemini_key[:10] + "..." if gemini_key else "MISSING")

from groq import Groq
client = Groq(api_key=groq_key)
r = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "say hi in one word"}],
    max_tokens=10
)
print("Groq:", r.choices[0].message.content)

from google import genai
client_gemini = genai.Client(api_key=gemini_key)
response = client_gemini.models.generate_content(
    model="gemini-2.5-flash",
    contents="say hi in one word"
)
print("Gemini:", response.text)


from faster_whisper import WhisperModel
WhisperModel("tiny", device="cpu", compute_type="int8")
print("Whisper: OK")

print("=" * 40)
print("ALL GOOD. Start building.")