import os
import json
from groq import Groq
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── OUTPUT SCHEMA ────────────────────────────────────────────
class MedResponse(BaseModel):
    possible_conditions: list[str]
    reasoning: str
    recommended_next_steps: list[str]
    red_flags_noted: list[str]
    is_emergency: bool
    confidence: float
    disclaimer: str = (
        "⚠️ MedAssist is for informational support only. "
        "It is NOT a substitute for a licensed healthcare professional. "
        "Always consult a qualified doctor for medical decisions."
    )

# ── SYSTEM PROMPT ────────────────────────────────────────────
SYSTEM_PROMPT = """You are MedAssist, an AI medical information assistant.

STRICT RULES — follow these in every single response:
1. NEVER make a definitive diagnosis. Always say 'possible conditions include' or 'this may suggest'
2. ALWAYS recommend consulting a licensed doctor
3. For chest pain, difficulty breathing, stroke signs, severe bleeding, 
   or loss of consciousness — set is_emergency to true immediately
4. Explain your reasoning clearly and transparently
5. Suggest specific next steps — which doctor to see, which tests to get
6. If information is insufficient, say so — never guess blindly
7. Be empathetic and calm in tone

Return ONLY valid JSON matching this exact structure:
{
  "possible_conditions": ["condition 1", "condition 2"],
  "reasoning": "clear explanation of your thinking",
  "recommended_next_steps": ["step 1", "step 2"],
  "red_flags_noted": ["any concerning symptoms"],
  "is_emergency": true or false,
  "confidence": 0.0 to 1.0
}"""

# ── EMERGENCY KEYWORDS ───────────────────────────────────────
EMERGENCY_KEYWORDS = [
    "chest pain", "chest tightness", "heart attack",
    "can't breathe", "cannot breathe", "difficulty breathing",
    "shortness of breath", "stroke", "face drooping",
    "arm weakness", "slurred speech", "severe bleeding",
    "unconscious", "loss of consciousness", "seizure",
    "anaphylaxis", "allergic reaction", "overdose",
    "poisoning", "coughing blood", "vomiting blood",
    "paralysis", "sudden vision loss"
]

# ── SAFETY WRAPPER ───────────────────────────────────────────
EMERGENCY_ALERT = (
    "🚨 URGENT: Based on your symptoms, please seek emergency "
    "medical care IMMEDIATELY. Call 112 / 911 or go to the "
    "nearest ER. Do not wait."
)

def check_emergency(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in EMERGENCY_KEYWORDS)

# ── MAIN FUNCTION ────────────────────────────────────────────
def process_text(
    user_input: str,
    chat_history: list = []
) -> dict:

    # build messages with history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += chat_history
    messages.append({"role": "user", "content": user_input})

    # call Groq
    response = client.chat.completions.create(
       model="qwen/qwen3.8-27b",
        messages=messages,
        max_tokens=1000,
        temperature=0.3
    )

    raw = response.choices[0].message.content.strip()

    # clean markdown fences if model adds them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    # parse JSON
    try:
        data = json.loads(raw)
        parsed = MedResponse(**data)
    except Exception as e:
        return {
            "error": f"Parse failed: {e}",
            "raw": raw,
            "status": "failed"
        }

    # emergency check on user input
    is_emergency = check_emergency(user_input) or parsed.is_emergency

    print("CONFIDENCE:", parsed.confidence)
    
    return {
        "status": "success",
        "is_emergency": is_emergency,
        "emergency_alert": EMERGENCY_ALERT if is_emergency else None,
        "response": parsed.model_dump(),
        "needs_review": parsed.confidence < 0.8
    }


# ── TEST ─────────────────────────────────────────────────────
if __name__ == "__main__":

    # test 1 — normal symptom
    print("\n--- TEST 1: normal symptom ---")
    result = process_text("I have a fever of 101F and body aches since yesterday")
    print("Emergency:", result["is_emergency"])
    print("Conditions:", result["response"]["possible_conditions"])
    print("Next steps:", result["response"]["recommended_next_steps"])
    print("Confidence:", result["response"]["confidence"])
    print("Needs review:", result["needs_review"])

    # test 2 — emergency symptom
    print("\n--- TEST 2: emergency ---")
    result = process_text("I have severe chest pain and my left arm is hurting")
    print("Emergency:", result["is_emergency"])
    print("Alert:", result["emergency_alert"])

    # test 3 — with chat history
    print("\n--- TEST 3: with history ---")
    history = [
        {"role": "user", "content": "I have diabetes"},
        {"role": "assistant", "content": "Noted. I will keep that in mind."}
    ]
    result = process_text("my blood sugar feels very low right now", history)
    print("Emergency:", result["is_emergency"])
    print("Conditions:", result["response"]["possible_conditions"])

    print("\n✅ text agent working")