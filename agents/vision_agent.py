import os
import base64
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from google import genai
#GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

load_dotenv()

# ── GEMINI CLIENT ────────────────────────────────────────────
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── OUTPUT SCHEMAS ───────────────────────────────────────────
# each image type has its own output structure
# because a prescription has different fields than an X-ray

class PrescriptionOutput(BaseModel):
    # what we extract from a handwritten prescription
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    date: Optional[str] = None
    medications: list[dict]   # list of {name, dosage, frequency, duration}
    diagnosis: Optional[str] = None
    confidence: float
    low_confidence_reason: Optional[str] = None

class ScanOutput(BaseModel):
    # what we extract from X-ray, CT, MRI, sonography
    scan_type: str            # xray / ct_scan / mri / sonography
    body_region: str          # chest / abdomen / head / knee etc
    observable_findings: list[str]   # what is visible
    abnormalities_noted: list[str]   # anything concerning
    image_quality: str        # good / poor / unreadable
    confidence: float
    low_confidence_reason: Optional[str] = None
    requires_specialist_review: bool

# ── HELPER: load image as base64 ─────────────────────────────
def load_image_as_base64(image_path: str) -> tuple[str, str]:
    """
    reads image from disk and converts to base64 string.
    base64 is needed because the Gemini API receives
    data as text — not raw binary files.
    returns: (base64_string, mime_type)
    """
    path = Path(image_path)
    ext = path.suffix.lower()

    # map file extension to MIME type
    # MIME type tells the API what kind of image it is
    mime_map = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(ext, "image/jpeg")

    # read file as binary and encode to base64
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    return image_data, mime_type

# ── HELPER: clean JSON from Gemini response ──────────────────
def parse_gemini_json(raw: str) -> dict:
    """
    Gemini sometimes wraps JSON in markdown code fences like:
```json
    { ... }
```
    this function strips those and returns clean JSON
    """
    raw = raw.strip()
    if raw.startswith("```"):
        # remove opening fence
        raw = raw.split("```")[1]
        # remove 'json' label if present
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    return json.loads(raw)

# ── PRESCRIPTION AGENT ───────────────────────────────────────
def extract_prescription(image_path: str) -> dict:
    """
    sends a handwritten prescription image to Gemini.
    extracts medications, dosages, frequencies.
    this replaces OCR — Gemini reads handwriting directly.
    """
    image_data, mime_type = load_image_as_base64(image_path)

    prompt = """You are a medical data extraction assistant.
Extract all information from this handwritten prescription image.

Return ONLY valid JSON with this exact structure:
{
  "patient_name": "string or null",
  "doctor_name": "string or null", 
  "date": "string or null",
  "diagnosis": "string or null",
  "medications": [
    {
      "name": "medication name",
      "dosage": "e.g. 500mg",
      "frequency": "e.g. BD, TDS, 1-0-1, SOS",
      "duration": "e.g. 5 days",
      "instructions": "e.g. after food or null"
    }
  ],
  "confidence": 0.0 to 1.0,
  "low_confidence_reason": "reason if confidence below 0.8 else null"
}

Confidence guide:
- 0.9-1.0: clearly legible, all fields readable
- 0.7-0.9: mostly legible, minor unclear sections  
- 0.5-0.7: partially legible, some medications unclear
- below 0.5: very hard to read, needs human review

Return ONLY the JSON. No explanation."""

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

    raw = response.text
    data = parse_gemini_json(raw)
    result = PrescriptionOutput(**data)

    return {
        "input_type": "prescription",
        "data": result.model_dump(),
        "is_emergency": False,
        "needs_review": result.confidence < 0.8,
        "confidence": result.confidence
    }

# ── MEDICAL SCAN AGENT ───────────────────────────────────────
def extract_scan(image_path: str, scan_type: str = "unknown") -> dict:
    """
    sends a medical scan image to Gemini.
    handles X-ray, CT scan, MRI, sonography.
    IMPORTANT: we describe findings only — never diagnose.
    the doctor reviews before patient sees this.
    """
    image_data, mime_type = load_image_as_base64(image_path)

    prompt = f"""You are assisting a licensed doctor by describing 
findings in this {scan_type} image.

CRITICAL RULES:
- DO NOT make a diagnosis
- DO NOT say "the patient has X"
- ONLY describe what is observable in the image
- Use medical terminology correctly
- If image quality is poor, say so

Return ONLY valid JSON:
{{
  "scan_type": "{scan_type}",
  "body_region": "chest / abdomen / head / knee / other",
  "observable_findings": [
    "finding 1",
    "finding 2"
  ],
  "abnormalities_noted": [
    "any abnormal finding or empty list if none"
  ],
  "image_quality": "good / poor / unreadable",
  "confidence": 0.0 to 1.0,
  "low_confidence_reason": "reason or null",
  "requires_specialist_review": true or false
}}

Return ONLY the JSON."""

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

    raw = response.text
    data = parse_gemini_json(raw)
    result = ScanOutput(**data)

    # scans always go to HITL — too important to auto-approve
    # doctor must always review scan findings before patient sees them
    return {
        "input_type": scan_type,
        "data": result.model_dump(),
        "is_emergency": len(result.abnormalities_noted) > 0,
        "needs_review": True,  # always True for scans
        "confidence": result.confidence
    }

# ── GENERAL IMAGE AGENT ──────────────────────────────────────
def extract_general_image(image_path: str) -> dict:
    """
    handles any other medical image —
    skin photos, wound photos, rashes, etc.
    """
    image_data, mime_type = load_image_as_base64(image_path)

    prompt = """You are assisting a doctor by describing what is 
visible in this medical image.

RULES:
- Describe only what you can see
- Do not diagnose
- Note if this does not appear to be a medical image

Return ONLY valid JSON:
{
  "image_description": "what is visible",
  "medical_relevance": "what medical information can be extracted",
  "observable_findings": ["finding 1", "finding 2"],
  "confidence": 0.0 to 1.0,
  "low_confidence_reason": "or null",
  "requires_specialist_review": true or false
}"""

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

    raw = response.text
    data = parse_gemini_json(raw)

    return {
        "input_type": "image",
        "data": data,
        "is_emergency": False,
        "needs_review": data.get("confidence", 1.0) < 0.8,
        "confidence": data.get("confidence", 1.0)
    }

# ── MAIN ENTRY POINT ─────────────────────────────────────────
def process_image(image_path: str, image_type: str = "auto") -> dict:
    """
    main function — routes image to correct handler.
    image_type can be:
      - prescription
      - xray
      - ct_scan
      - mri
      - sonography
      - auto (classifier will detect)
    """
    if image_type == "prescription":
        return extract_prescription(image_path)
    elif image_type in ["xray", "ct_scan", "mri", "sonography", "bone_scan"]:
        return extract_scan(image_path, image_type)
    else:
        return extract_general_image(image_path)


# ── TEST ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    # test with a real image if you have one
    # put any medical image in your project folder and test it
    test_image = "test_xray.jpg"  # change this to your image

    if not Path(test_image).exists():
        print(f"No test image found at {test_image}")
        print("Create a test by placing any image in the project folder")
        print("and updating the test_image variable above")
        sys.exit(0)

    print("\n--- TEST: xray ---")
    result = process_image(test_image, "x_ray")
    print("Input type:", result["input_type"])
    print("Confidence:", result["confidence"])
    print("Needs review:", result["needs_review"])
    print("Medications:", result["data"].get("medications"))

    print("\n✅ vision agent working")