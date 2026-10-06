import os
import base64
import json
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from google import genai

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── STEP 1: ANALYSE WHAT A PAGE CONTAINS ────────────────────
def analyse_page(page) -> dict:
    """
    looks at one PDF page and returns what it contains.
    this tells us which processing path to take.
    """
    # extract text layer
    text = page.get_text().strip()
    has_text = len(text) > 30  # more than 30 chars = real text

    # extract embedded images
    image_list = page.get_images(full=True)
    images = []

    for img in image_list:
        xref = img[0]  # xref is the image reference number
        base_image = page.parent.extract_image(xref)
        image_bytes = base_image["image"]
        images.append(image_bytes)

    return {
        "has_text":    len(text) > 30,
        "has_images":  len(images) > 0,
        "text":        text,
        "images":      images,
        "image_count": len(images)
    }

# ── STEP 2: ANALYSE EMBEDDED IMAGE ──────────────────────────
def analyse_embedded_image(image_bytes: bytes, page_num: int, img_num: int) -> dict:
    """
    sends one embedded image to Gemini.
    only processes medical images — skips logos and signatures.
    """
    image_b64 = base64.b64encode(image_bytes).decode()

    # detect image type from bytes header
    if image_bytes[:3] == b'\xff\xd8\xff':
        mime = "image/jpeg"
    elif image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        mime = "image/png"
    else:
        mime = "image/jpeg"

    prompt = f"""This image is embedded inside a medical PDF 
(page {page_num+1}, image {img_num+1}).

Identify what type of image this is and describe findings.

Return ONLY valid JSON:
{{
  "image_type": "xray / ecg / chart / lab_result / signature / logo / other",
  "is_medical": true or false,
  "findings": ["finding 1", "finding 2"],
  "body_region": "chest / abdomen / head / not applicable",
  "confidence": 0.0 to 1.0,
  "low_confidence_reason": "reason or null"
}}

If this is a logo, signature, or non-medical image,
set is_medical to false and findings to empty list.
Return ONLY the JSON."""

    response = gemini_client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=[{
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": mime, "data": image_b64}},
                {"text": prompt}
            ]
        }]
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except:
        return {
            "image_type": "unknown",
            "is_medical": False,
            "findings": [],
            "confidence": 0.0,
            "low_confidence_reason": "parse error"
        }

# ── STEP 3: HANDLE FULLY SCANNED PAGE ───────────────────────
def analyse_scanned_page(page, page_num: int) -> dict:
    """
    when a page has NO text and NO embedded images —
    the whole page IS the image (scanned document).
    renders the page as JPEG and sends to Gemini.
    """
    # render page as image at 150 DPI
    # 150 DPI = good quality for text reading, not too large
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("jpeg")
    image_b64 = base64.b64encode(img_bytes).decode()

    prompt = f"""This is page {page_num+1} of a scanned medical PDF.
Extract ALL medical information visible on this page.

Return ONLY valid JSON:
{{
  "page_type": "prescription / lab_report / discharge_summary / radiology_report / scan_image / other",
  "extracted_text": "all readable text from this page",
  "medications": [{{"name": "", "dosage": "", "frequency": ""}}],
  "lab_values": {{"parameter": "value"}},
  "findings": ["finding 1"],
  "doctor_name": "or null",
  "patient_name": "or null",
  "date": "or null",
  "confidence": 0.0 to 1.0,
  "low_confidence_reason": "or null"
}}
Return ONLY the JSON."""

    response = gemini_client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=[{
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                {"text": prompt}
            ]
        }]
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return {"type": "scanned_page", "page": page_num+1, "data": json.loads(raw)}
    except:
        return {"type": "scanned_page", "page": page_num+1, "data": {}, "error": "parse failed"}

# ── STEP 4: SYNTHESIZE ALL PAGES WITH GROQ ──────────────────
def synthesize_with_groq(all_page_results: list, filename: str) -> dict:
    """
    after processing all pages, send everything to Groq.
    Groq combines text findings + image findings
    into one coherent medical summary.
    """
    combined = json.dumps(all_page_results, indent=2)

    prompt = f"""You are analyzing a medical PDF called '{filename}'.
Below is extracted content from every page — 
both text portions and embedded image findings.

Synthesize into a single medical summary.

Return ONLY valid JSON:
{{
  "document_type": "lab_report / discharge_summary / radiology_report / prescription / mixed",
  "patient_name": "or null",
  "date": "or null",
  "doctor_name": "or null",
  "key_findings": ["finding 1", "finding 2"],
  "medications": [{{"name": "", "dosage": "", "frequency": ""}}],
  "lab_values": {{"parameter": "value with unit"}},
  "abnormal_flags": ["abnormal value 1"],
  "embedded_scan_findings": ["finding from xray or scan if present"],
  "summary": "2-3 sentence plain English summary",
  "requires_doctor_review": true or false,
  "confidence": 0.0 to 1.0
}}

Extracted content:
{combined}

Return ONLY the JSON."""

    response = groq_client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.3
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except:
        return {
            "error": "synthesis failed",
            "raw": raw
        }

# ── MAIN: PROCESS ANY PDF ────────────────────────────────────
def process_pdf(pdf_path: str) -> dict:
    """
    main entry point.
    handles ALL PDF types automatically:
    - digital (text only)
    - scanned (image only)
    - mixed (text + embedded images)
    - multi-page (any combination)
    """
    import fitz  # pymupdf

    doc = fitz.open(pdf_path)
    filename = Path(pdf_path).name
    all_page_results = []

    print(f"Processing {filename} — {len(doc)} pages")

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_analysis = analyse_page(page)

        print(f"  Page {page_num+1}: "
              f"text={page_analysis['has_text']}, "
              f"images={page_analysis['image_count']}")

        page_result = {
            "page": page_num + 1,
            "components": []
        }

        # ── CASE 1: page has text ──
        if page_analysis["has_text"]:
            page_result["components"].append({
                "type": "text",
                "content": page_analysis["text"]
            })

        # ── CASE 2: page has embedded images ──
        if page_analysis["has_images"]:
            for img_num, image_bytes in enumerate(page_analysis["images"]):
                print(f"    Analysing embedded image {img_num+1}...")
                image_findings = analyse_embedded_image(
                    image_bytes, page_num, img_num
                )
                # only include medical images — skip logos
                if image_findings.get("is_medical"):
                    page_result["components"].append({
                        "type": "embedded_medical_image",
                        "image_number": img_num + 1,
                        "findings": image_findings
                    })
                else:
                    print(f"    Skipping non-medical image "
                          f"({image_findings.get('image_type')})")
                          
        # ── CASE 3: page has NOTHING ──
        # whole page is a scanned image
        if not page_analysis["has_text"] and not page_analysis["has_images"]:
            print(f"    Page {page_num+1} is fully scanned — rendering...")
            scanned = analyse_scanned_page(page, page_num)
            page_result["components"].append(scanned)

        all_page_results.append(page_result)

    # synthesize everything
    print("Synthesizing with Groq...")
    summary = synthesize_with_groq(all_page_results, filename)

    return {
        "filename": filename,
        "total_pages": len(doc),
        "page_results": all_page_results,
        "summary": summary,
        "input_type": "pdf",
        "needs_review": (
            summary.get("confidence", 1.0) < 0.8 or
            summary.get("requires_doctor_review", False)
        ),
        "confidence": summary.get("confidence", 1.0)
    }


# ── TEST ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    test_pdf = "test_report.pdf"

    if not Path(test_pdf).exists():
        print(f"\nNo test PDF found at {test_pdf}")
        print("To test PDF parser:")
        print("1. Put any medical PDF in your project folder")
        print("2. Rename it to test_report.pdf")
        print("3. Run python -m utils.pdf_parser again")
        print("\n✅ PDF parser ready — add test_report.pdf to test fully")
        sys.exit(0)

    print(f"\n--- TEST: processing {test_pdf} ---")
    result = process_pdf(test_pdf)

    print("\n===== SUMMARY =====")
    print("Document type:", result["summary"].get("document_type"))
    print("Patient:", result["summary"].get("patient_name"))
    print("Key findings:", result["summary"].get("key_findings"))
    print("Abnormal flags:", result["summary"].get("abnormal_flags"))
    print("Needs review:", result["needs_review"])
    print("Confidence:", result["confidence"])
    print("\n✅ PDF parser working")