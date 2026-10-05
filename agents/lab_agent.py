import os
import json
from groq import Groq
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── NORMAL RANGES ────────────────────────────────────────────
# these are standard medical reference ranges
# format: "parameter": (min, max, unit)
# None means no lower limit or no upper limit

NORMAL_RANGES = {
    # blood sugar
    "hba1c":              (0,    5.7,   "%"),
    "fasting_glucose":    (70,   100,   "mg/dL"),
    "random_glucose":     (0,    200,   "mg/dL"),
    "postprandial_glucose": (0,  140,   "mg/dL"),

    # complete blood count (CBC)
    "haemoglobin":        (12,   17,    "g/dL"),
    "hemoglobin":         (12,   17,    "g/dL"),
    "wbc":                (4000, 11000, "/µL"),
    "rbc":                (4.5,  5.5,   "million/µL"),
    "platelets":          (150000, 400000, "/µL"),
    "hematocrit":         (36,   50,    "%"),
    "mcv":                (80,   100,   "fL"),
    "mch":                (27,   33,    "pg"),

    # lipid profile
    "total_cholesterol":  (0,    200,   "mg/dL"),
    "ldl":                (0,    100,   "mg/dL"),
    "hdl":                (40,   60,    "mg/dL"),
    "triglycerides":      (0,    150,   "mg/dL"),

    # liver function
    "sgpt":               (0,    40,    "U/L"),
    "sgot":               (0,    40,    "U/L"),
    "bilirubin":          (0,    1.2,   "mg/dL"),
    "alkaline_phosphatase": (44, 147,   "U/L"),

    # kidney function
    "creatinine":         (0.6,  1.2,   "mg/dL"),
    "urea":               (7,    20,    "mg/dL"),
    "uric_acid":          (2.4,  7.0,   "mg/dL"),

    # thyroid
    "tsh":                (0.4,  4.0,   "mIU/L"),
    "t3":                 (80,   200,   "ng/dL"),
    "t4":                 (5,    12,    "µg/dL"),

    # vitals
    "systolic_bp":        (90,   120,   "mmHg"),
    "diastolic_bp":       (60,   80,    "mmHg"),
    "heart_rate":         (60,   100,   "bpm"),
    "spo2":               (95,   100,   "%"),
    "temperature":        (97,   99,    "°F"),
}

# ── PYDANTIC OUTPUT ──────────────────────────────────────────
class LabResult(BaseModel):
    parameter: str
    value: float
    unit: str
    status: str        # normal / high / low
    normal_range: str  # e.g. "70-100 mg/dL"

class LabAnalysis(BaseModel):
    total_parameters: int
    abnormal_count: int
    abnormal_parameters: list[LabResult]
    normal_parameters: list[LabResult]
    clinical_summary: str
    possible_conditions: list[str]
    recommended_next_steps: list[str]
    confidence: float
    is_emergency: bool
    disclaimer: str = (
        "⚠️ Lab analysis is informational only. "
        "Always consult a doctor to interpret your results."
    )

# ── HELPER: extract numeric value ────────────────────────────
def extract_number(value_str: str) -> Optional[float]:
    """
    extracts the numeric part from a string like:
    "9.2%" → 9.2
    "210 mg/dL" → 210
    "11,000 /µL" → 11000
    """
    import re
    # remove commas (11,000 → 11000)
    cleaned = str(value_str).replace(",", "")
    # find first number in string
    match = re.search(r"[\d.]+", cleaned)
    if match:
        return float(match.group())
    return None

# ── HELPER: check one value against normal range ─────────────
def check_value(param: str, value_str: str) -> Optional[LabResult]:
    """
    checks a single lab value against its normal range.
    returns LabResult with status: normal / high / low
    returns None if parameter not in our known ranges
    """
    param_lower = param.lower().replace(" ", "_").replace("-", "_")

    if param_lower not in NORMAL_RANGES:
        return None

    min_val, max_val, unit = NORMAL_RANGES[param_lower]
    numeric_value = extract_number(value_str)

    if numeric_value is None:
        return None

    # determine status
    if numeric_value < min_val:
        status = "low"
    elif numeric_value > max_val:
        status = "high"
    else:
        status = "normal"

    return LabResult(
        parameter=param,
        value=numeric_value,
        unit=unit,
        status=status,
        normal_range=f"{min_val}-{max_val} {unit}"
    )

# ── MAIN: analyse lab values ─────────────────────────────────
def analyse_lab_values(lab_data: dict) -> dict:
    """
    main function.
    takes a dict of lab values like:
    {"HbA1c": "9.2%", "fasting_glucose": "210 mg/dL"}
    returns full analysis with abnormal flags + clinical summary
    """

    normal_params = []
    abnormal_params = []

    # step 1 — check each value against normal ranges
    for param, value in lab_data.items():
        result = check_value(param, str(value))
        if result:
            if result.status == "normal":
                normal_params.append(result)
            else:
                abnormal_params.append(result)

    # step 2 — build summary for Groq
    if abnormal_params:
        abnormal_summary = "\n".join([
            f"- {r.parameter}: {r.value} {r.unit} ({r.status.upper()}, normal: {r.normal_range})"
            for r in abnormal_params
        ])
    else:
        abnormal_summary = "All values within normal range"

    # step 3 — send to Groq for clinical interpretation
    prompt = f"""You are a medical assistant analyzing lab results.

The following lab values are ABNORMAL:
{abnormal_summary}

Total parameters checked: {len(normal_params) + len(abnormal_params)}
Abnormal count: {len(abnormal_params)}

Provide a clinical interpretation.
Return ONLY valid JSON:
{{
  "clinical_summary": "2-3 sentence plain English summary of what these results mean together",
  "possible_conditions": ["condition 1", "condition 2"],
  "recommended_next_steps": ["step 1", "step 2", "step 3"],
  "confidence": 0.0 to 1.0,
  "is_emergency": true or false
}}

Rules:
- Never make a definitive diagnosis
- Say 'may suggest' or 'could indicate'
- is_emergency is true only for critical values
  (e.g. glucose below 50 or above 500, haemoglobin below 7)
- Return ONLY the JSON"""

    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.3
    )

    raw = response.choices[0].message.content.strip()

    # clean markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        groq_output = json.loads(raw)
    except:
        groq_output = {
            "clinical_summary": "Unable to parse clinical summary",
            "possible_conditions": [],
            "recommended_next_steps": ["Please consult a doctor"],
            "confidence": 0.5,
            "is_emergency": False
        }

    # step 4 — build final response
    analysis = LabAnalysis(
        total_parameters=len(normal_params) + len(abnormal_params),
        abnormal_count=len(abnormal_params),
        abnormal_parameters=abnormal_params,
        normal_parameters=normal_params,
        clinical_summary=groq_output["clinical_summary"],
        possible_conditions=groq_output["possible_conditions"],
        recommended_next_steps=groq_output["recommended_next_steps"],
        confidence=groq_output["confidence"],
        is_emergency=groq_output["is_emergency"]
    )

    return {
        "input_type": "lab_values",
        "data": analysis.model_dump(),
        "is_emergency": analysis.is_emergency,
        "needs_review": analysis.confidence < 0.8 or len(abnormal_params) > 3,
        "confidence": analysis.confidence
    }


# ── TEST ─────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n--- TEST 1: diabetic patient values ---")
    result = analyse_lab_values({
        "HbA1c": "9.2%",
        "fasting_glucose": "210 mg/dL",
        "ldl": "160 mg/dL",
        "hdl": "38 mg/dL",
        "haemoglobin": "11.2 g/dL"
    })
    print("Abnormal count:", result["data"]["abnormal_count"])
    print("Is emergency:", result["is_emergency"])
    print("Needs review:", result["needs_review"])
    print("Summary:", result["data"]["clinical_summary"])
    print("Conditions:", result["data"]["possible_conditions"])
    print("Next steps:", result["data"]["recommended_next_steps"])

    print("\n--- TEST 2: normal values ---")
    result = analyse_lab_values({
        "haemoglobin": "14.5 g/dL",
        "fasting_glucose": "88 mg/dL",
        "tsh": "2.1 mIU/L"
    })
    print("Abnormal count:", result["data"]["abnormal_count"])
    print("Summary:", result["data"]["clinical_summary"])

    print("\n--- TEST 3: emergency values ---")
    result = analyse_lab_values({
        "fasting_glucose": "520 mg/dL",
        "haemoglobin": "6.2 g/dL"
    })
    print("Is emergency:", result["is_emergency"])
    print("Summary:", result["data"]["clinical_summary"])

    print("\n✅ lab agent working")