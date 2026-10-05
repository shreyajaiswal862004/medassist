import os
import base64
from pathlib import Path
from enum import Enum
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── INPUT TYPES ──────────────────────────────────────────────
# all possible input types the classifier can detect
class InputType(str, Enum):
    TEXT                = "text"
    VOICE               = "voice"
    PRESCRIPTION        = "prescription"
    XRAY                = "xray"
    CT_SCAN             = "ct_scan"
    MRI                 = "mri"
    SONOGRAPHY          = "sonography"
    BONE_SCAN           = "bone_scan"
    PDF_DIGITAL         = "pdf_digital"
    PDF_SCANNED         = "pdf_scanned"
    PDF_MIXED           = "pdf_mixed"
    LAB_VALUES          = "lab_values"
    SENSOR_DATA         = "sensor_data"
    MEDICAL_REPORT_TEXT = "medical_report_text"
    UNKNOWN             = "unknown"

# ── FILE EXTENSION MAP ───────────────────────────────────────
# first check — fast, no API call needed
# just look at the file extension
EXTENSION_MAP = {
    ".jpg":  "image",
    ".jpeg": "image",
    ".png":  "image",
    ".webp": "image",
    ".pdf":  "pdf",
    ".mp3":  "voice",
    ".wav":  "voice",
    ".m4a":  "voice",
    ".ogg":  "voice",
}

# ── STEP 1: DETECT BROAD CATEGORY FROM FILE ──────────────────
def detect_broad_category(file_path: str = None, text_input: str = None) -> str:
    """
    fast first check — no API call.
    just looks at file extension or whether input is text.
    returns: 'image', 'pdf', 'voice', 'text', 'structured'
    """
    # no file — it's text or structured data
    if not file_path:
        return "text"

    ext = Path(file_path).suffix.lower()
    return EXTENSION_MAP.get(ext, "unknown")

# ── STEP 2: CLASSIFY IMAGE TYPE ──────────────────────────────
def classify_image(file_path: str) -> InputType:
    """
    for image files — uses Gemini vision to detect
    what TYPE of medical image it is.
    prescription vs xray vs ct scan vs sonography etc.
    """
    ext = Path(file_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png",  ".webp": "image/webp"
    }
    mime_type = mime_map.get(ext, "image/jpeg")

    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    prompt = """Look at this medical image and classify it.
Reply with ONLY one of these exact labels — nothing else:

- prescription       (handwritten doctor prescription)
- xray               (X-ray image)
- ct_scan            (CT scan image)
- mri                (MRI scan image)
- sonography         (ultrasound / sonography image)
- bone_scan          (nuclear bone scan)
- medical_report_text (photo of a typed medical report)
- unknown            (not a medical image or cannot determine)

Reply with the single label only."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_data
                        }
                    },
                    {"text": prompt}
                ]
            }
        ]
    )

    label = response.text.strip().lower()

    # map label to InputType enum
    type_map = {
        "prescription":        InputType.PRESCRIPTION,
        "xray":                InputType.XRAY,
        "ct_scan":             InputType.CT_SCAN,
        "mri":                 InputType.MRI,
        "sonography":          InputType.SONOGRAPHY,
        "bone_scan":           InputType.BONE_SCAN,
        "medical_report_text": InputType.MEDICAL_REPORT_TEXT,
    }

    return type_map.get(label, InputType.UNKNOWN)

# ── STEP 3: CLASSIFY TEXT INPUT ──────────────────────────────
def classify_text(text_input: str) -> InputType:
    """
    for text inputs — uses Groq to detect
    whether it's symptoms, a medical report, or lab values.
    """
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = f"""Classify this medical text input into one category.
Reply with ONLY the label — nothing else.

Categories:
- text               (patient describing symptoms or asking a question)
- medical_report_text (typed medical report, discharge summary)
- lab_values         (blood test results, CBC values, HbA1c etc)
- sensor_data        (smartwatch data, BP readings, pulse rate)

Text to classify:
{text_input[:500]}

Reply with the single label only."""

    response = groq_client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20,
        temperature=0
    )

    label = response.choices[0].message.content.strip().lower()

    type_map = {
        "text":                InputType.TEXT,
        "medical_report_text": InputType.MEDICAL_REPORT_TEXT,
        "lab_values":          InputType.LAB_VALUES,
        "sensor_data":         InputType.SENSOR_DATA,
    }

    return type_map.get(label, InputType.TEXT)

# ── STEP 4: CLASSIFY PDF ─────────────────────────────────────
def classify_pdf(file_path: str) -> InputType:
    """
    for PDFs — checks if it has extractable text or not.
    digital PDF → has text → pdf_digital
    scanned PDF → no text → pdf_scanned
    mixed PDF   → has text AND embedded images → pdf_mixed
    """
    import fitz  # pymupdf

    doc = fitz.open(file_path)
    page = doc[0]  # check first page

    text = page.get_text().strip()
    images = page.get_images(full=True)

    has_text = len(text) > 30
    has_images = len(images) > 0

    if has_text and has_images:
        return InputType.PDF_MIXED
    elif has_text:
        return InputType.PDF_DIGITAL
    else:
        return InputType.PDF_SCANNED

# ── MAIN CLASSIFIER ──────────────────────────────────────────
def classify_input(
    file_path: str = None,
    text_input: str = None,
    structured_data: dict = None
) -> InputType:
    """
    main entry point.
    call this with whatever the user sent.
    returns the InputType so the orchestrator knows
    which agent to route to.
    """

    # structured data → lab values or sensor data
    if structured_data:
        # check keys to determine type
        lab_keys = ["hba1c", "glucose", "wbc", "rbc", "haemoglobin",
                    "hemoglobin", "platelets", "cbc", "ldl", "hdl"]
        sensor_keys = ["heart_rate", "bp", "blood_pressure",
                       "spo2", "steps", "temperature"]

        keys_lower = [k.lower() for k in structured_data.keys()]

        if any(k in keys_lower for k in lab_keys):
            return InputType.LAB_VALUES
        elif any(k in keys_lower for k in sensor_keys):
            return InputType.SENSOR_DATA
        else:
            return InputType.LAB_VALUES  # default for structured

    # no file, has text → classify text
    if text_input and not file_path:
        return classify_text(text_input)

    # has file → check extension first
    if file_path:
        broad = detect_broad_category(file_path)

        if broad == "image":
            # use Gemini to detect exact image type
            return classify_image(file_path)

        elif broad == "pdf":
            # check PDF content type
            return classify_pdf(file_path)

        elif broad == "voice":
            return InputType.VOICE

    return InputType.UNKNOWN


# ── TEST ─────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n--- TEST 1: text symptom ---")
    result = classify_input(text_input="I have fever and headache since 2 days")
    print("Classified as:", result)

    print("\n--- TEST 2: lab values text ---")
    result = classify_input(text_input="HbA1c: 9.2%, Fasting glucose: 210 mg/dL, WBC: 11000")
    print("Classified as:", result)

    print("\n--- TEST 3: structured lab values ---")
    result = classify_input(structured_data={"HbA1c": "9.2%", "glucose": "210 mg/dL"})
    print("Classified as:", result)

    print("\n--- TEST 4: prescription image ---")
    from pathlib import Path
    if Path("test_prescription.jpg").exists():
        result = classify_input(file_path="test_prescription.jpg")
        print("Classified as:", result)
    else:
        print("No test image found — skipping")

    print("\n✅ classifier working")