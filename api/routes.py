from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
from fastapi import UploadFile, File

from utils.db import get_db
from api.auth import (
    RegisterRequest, LoginRequest,
    register_user, login_user,
    get_current_user, require_doctor,
    require_admin, require_patient
)
from agents.text_agent import process_text
from agents.safety import validate_input, apply_safety

router = APIRouter()

# ══════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════

@router.post("/auth/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user — patient, doctor, or admin"""
    return register_user(request, db)

@router.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login and get JWT token"""
    return login_user(request, db)

@router.get("/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current logged in user info from token"""
    return current_user

# ══════════════════════════════════════════════════════════════
# PATIENT ROUTES
# ══════════════════════════════════════════════════════════════

@router.post("/chat")
def chat(
    
    message: str,
    current_user: dict = Depends(require_patient),
    db: Session = Depends(get_db)
):
    print("CHAT ENDPOINT HIT - user:", current_user)
    import traceback
    try:
        from sqlalchemy import text

        validation = validate_input(message)
        if not validation.is_valid:
            raise HTTPException(status_code=400, detail=validation.error)

        history = db.execute(text("""
            SELECT role, content FROM messages
            WHERE session_id IN (
                SELECT id FROM chat_sessions
                WHERE patient_id = :patient_id AND is_active = true
            )
            ORDER BY timestamp DESC LIMIT 10
        """), {"patient_id": current_user["user_id"]}).fetchall()

        chat_history = [
            {"role": row.role, "content": row.content}
            for row in reversed(history)
        ]

        result = process_text(validation.cleaned_input, chat_history)

        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail="AI processing failed")

        safe_response = apply_safety(message, result["response"])

        # save to database
        from sqlalchemy import text as sql_text

        # get or create active session
        session = db.execute(sql_text("""
            SELECT id FROM chat_sessions
            WHERE patient_id = :patient_id AND is_active = true
            ORDER BY created_at DESC LIMIT 1
        """), {"patient_id": current_user["user_id"]}).fetchone()

        if not session:
            session_result = db.execute(sql_text("""
                INSERT INTO chat_sessions (patient_id)
                VALUES (:patient_id) RETURNING id
            """), {"patient_id": current_user["user_id"]})
            db.commit()
            session_id = session_result.fetchone()[0]
        else:
            session_id = session.id

        # save user message
        db.execute(sql_text("""
            INSERT INTO messages (session_id, role, content, input_type, is_emergency)
            VALUES (:session_id, 'user', :content, 'text', :is_emergency)
        """), {
            "session_id": session_id,
            "content": message,
            "is_emergency": safe_response["is_emergency"]
        })

        # save AI response
        db.execute(sql_text("""
            INSERT INTO messages
            (session_id, role, content, input_type, is_emergency, confidence)
            VALUES (:session_id, 'assistant', :content, 'text', :is_emergency, :confidence)
        """), {
            "session_id": session_id,
            "content": str(safe_response.get("possible_conditions", "")),
            "is_emergency": safe_response["is_emergency"],
            "confidence": safe_response["confidence"]
        })
        db.commit()

        # check needs review — save to hitl_reviews
        print("NEEDS REVIEW:", safe_response["needs_review"])
        if safe_response["needs_review"]:
            msg = db.execute(sql_text("""
                SELECT id FROM messages
                WHERE session_id = :session_id AND role = 'assistant'
                ORDER BY timestamp DESC LIMIT 1
            """), {"session_id": session_id}).fetchone()

            if msg:
                db.execute(sql_text("""
    INSERT INTO hitl_reviews (message_id, ai_output, confidence, original_message)
    VALUES (:message_id, :ai_output, :confidence, :original_message)
"""), {
    "message_id": msg.id,
    "ai_output": str(safe_response),
    "confidence": safe_response["confidence"],
    "original_message": message
})
                db.commit()
                print("SAVED TO HITL REVIEWS")

        return safe_response

    except HTTPException:
        raise
    except Exception as e:
        error_detail = traceback.format_exc()
        print("CHAT ERROR:", error_detail)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    message: str = None,
    current_user: dict = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """handles file uploads — images, PDFs, voice"""
    import shutil
    import uuid
    from fastapi import UploadFile, File
    from sqlalchemy import text

    # save file to uploads folder
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = f"uploads/{unique_filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # classify what was uploaded
    from agents.classifier import classify_input, InputType
    input_type = classify_input(file_path=file_path)

    # route to correct agent
    if input_type == InputType.PRESCRIPTION:
        from agents.vision_agent import extract_prescription
        result = extract_prescription(file_path)
        response_data = {
            "possible_conditions": ["Prescription analyzed"],
            "reasoning": f"Extracted {len(result['data'].get('medications', []))} medications",
            "recommended_next_steps": ["Review medications with your doctor"],
            "red_flags_noted": [],
            "is_emergency": False,
            "confidence": result["confidence"]
        }

    elif input_type in [InputType.XRAY, InputType.CT_SCAN,
                        InputType.MRI, InputType.SONOGRAPHY]:
        from agents.vision_agent import extract_scan
        result = extract_scan(file_path, input_type.value)
        response_data = {
            "possible_conditions": result["data"].get("observable_findings", []),
            "reasoning": f"Scan analysis: {', '.join(result['data'].get('observable_findings', []))}",
            "recommended_next_steps": ["Consult your doctor to review scan findings"],
            "red_flags_noted": result["data"].get("abnormalities_noted", []),
            "is_emergency": result["is_emergency"],
            "confidence": result["confidence"]
        }

    elif input_type in [InputType.PDF_DIGITAL,
                        InputType.PDF_SCANNED, InputType.PDF_MIXED]:
        from utils.pdf_parser import process_pdf
        result = process_pdf(file_path)
        summary = result["summary"]
        response_data = {
            "possible_conditions": summary.get("key_findings", []),
            "reasoning": summary.get("summary", ""),
            "recommended_next_steps": ["Review report with your doctor"],
            "red_flags_noted": summary.get("abnormal_flags", []),
            "is_emergency": False,
            "confidence": result["confidence"]
        }

    else:
        response_data = {
            "possible_conditions": ["File received"],
            "reasoning": "File type detected: " + str(input_type),
            "recommended_next_steps": ["Please describe your symptoms in text"],
            "red_flags_noted": [],
            "is_emergency": False,
            "confidence": 0.8
        }

    # apply safety wrapper
    from agents.safety import apply_safety
    safe_response = apply_safety(message or file.filename, response_data)

    return safe_response

@router.get("/patient/history")
def get_history(
    current_user: dict = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """Get patient's chat history"""
    from sqlalchemy import text

    messages = db.execute(text("""
        SELECT m.role, m.content, m.timestamp, m.is_emergency
        FROM messages m
        JOIN chat_sessions cs ON m.session_id = cs.id
        WHERE cs.patient_id = :patient_id
        ORDER BY m.timestamp DESC
        LIMIT 50
    """), {"patient_id": current_user["user_id"]}).fetchall()

    return {
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": str(msg.timestamp),
                "is_emergency": msg.is_emergency
            }
            for msg in messages
        ]
    }

@router.get("/patient/my-doctor")
def get_my_doctor(
    current_user: dict = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """Get the doctor assigned to this patient"""
    from sqlalchemy import text

    doctor = db.execute(text("""
        SELECT u.id, u.name, u.email
        FROM users u
        JOIN patients p ON u.id = p.assigned_doctor_id
        WHERE p.user_id = :patient_id
    """), {"patient_id": current_user["user_id"]}).fetchone()

    if not doctor:
        raise HTTPException(status_code=404, detail="No doctor assigned yet")

    return {
        "id": doctor.id,
        "name": doctor.name,
        "email": doctor.email
    }

@router.get("/patient/reports")
def get_my_reports(
    current_user: dict = Depends(require_patient),
    db: Session = Depends(get_db)
):
    """Get all uploaded reports and messages for this patient"""
    from sqlalchemy import text

    messages = db.execute(text("""
        SELECT m.role, m.content, m.input_type, 
               m.is_emergency, m.timestamp
        FROM messages m
        JOIN chat_sessions cs ON m.session_id = cs.id
        WHERE cs.patient_id = :patient_id
        AND m.role = 'user'
        AND m.input_type != 'text'
        ORDER BY m.timestamp DESC
    """), {"patient_id": current_user["user_id"]}).fetchall()

    return {
        "reports": [
            {
                "content": msg.content,
                "input_type": msg.input_type,
                "is_emergency": msg.is_emergency,
                "timestamp": str(msg.timestamp)
            }
            for msg in messages
        ]
    }

# ══════════════════════════════════════════════════════════════
# DOCTOR ROUTES
# ══════════════════════════════════════════════════════════════

@router.get("/doctor/patients")
def get_my_patients(
    current_user: dict = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Get all patients assigned to this doctor"""
    from sqlalchemy import text

    patients = db.execute(text("""
        SELECT u.id, u.name, u.email, u.created_at
        FROM users u
        JOIN patients p ON u.id = p.user_id
        WHERE p.assigned_doctor_id = :doctor_id
    """), {"doctor_id": current_user["user_id"]}).fetchall()

    return {
        "patients": [
            {
                "id": p.id,
                "name": p.name,
                "email": p.email,
                "joined": str(p.created_at)
            }
            for p in patients
        ]
    }

@router.get("/doctor/patient/{patient_id}")
def get_patient_details(
    patient_id: int,
    current_user: dict = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Get detailed patient info, chat history, and reports for doctor"""
    from sqlalchemy import text

    patient = db.execute(text("""
        SELECT u.id, u.name, u.email, u.created_at
        FROM users u
        WHERE u.id = :patient_id AND u.role = 'patient'
    """), {"patient_id": patient_id}).fetchone()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    messages = db.execute(text("""
        SELECT m.id, m.role, m.content, m.input_type, m.is_emergency, m.timestamp, m.confidence
        FROM messages m
        JOIN chat_sessions cs ON m.session_id = cs.id
        WHERE cs.patient_id = :patient_id
        ORDER BY m.timestamp DESC
        LIMIT 50
    """), {"patient_id": patient_id}).fetchall()

    return {
        "id": patient.id,
        "name": patient.name,
        "email": patient.email,
        "joined": str(patient.created_at),
        "history": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "input_type": msg.input_type,
                "is_emergency": msg.is_emergency,
                "confidence": msg.confidence,
                "timestamp": str(msg.timestamp)
            }
            for msg in messages
        ]
    }


@router.get("/doctor/review-queue")
def get_review_queue(
    current_user: dict = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Get all AI outputs pending doctor review"""
    from sqlalchemy import text

    reviews = db.execute(text("""
    SELECT
        hr.id, hr.confidence, hr.ai_output, hr.status,
        hr.original_message,
        u.name as patient_name,
        m.timestamp
    FROM hitl_reviews hr
    JOIN messages m ON hr.message_id = m.id
    JOIN chat_sessions cs ON m.session_id = cs.id
    JOIN users u ON cs.patient_id = u.id
    WHERE hr.status = 'pending'
    ORDER BY m.timestamp DESC
""")).fetchall()

    return {
        "pending_reviews": [
            {
                "review_id": r.id,
                "patient_name": r.patient_name,
                "original_message": r.original_message,
                "ai_output": r.ai_output,
                "confidence": r.confidence,
                "timestamp": str(r.timestamp)
            }
            for r in reviews
        ]
    }

@router.post("/doctor/review/{review_id}/decision")
def review_decision(
    review_id: int,
    decision: str,        # "approve", "edit", "reject"
    edited_response: str = None,
    current_user: dict = Depends(require_doctor),
    db: Session = Depends(get_db)
):
    """Doctor approves, edits, or rejects an AI response"""
    from sqlalchemy import text
    from datetime import datetime

    if decision not in ["approve", "edit", "reject"]:
        raise HTTPException(400, "Decision must be approve, edit, or reject")

    db.execute(text("""
        UPDATE hitl_reviews
        SET status = :status,
            doctor_id = :doctor_id,
            doctor_edit = :doctor_edit,
            reviewed_at = :reviewed_at
        WHERE id = :review_id
    """), {
        "status": decision + "d",
        "doctor_id": current_user["user_id"],
        "doctor_edit": edited_response,
        "reviewed_at": datetime.utcnow(),
        "review_id": review_id
    })
    db.commit()

    return {"message": f"Review {decision}d successfully"}

# ══════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ══════════════════════════════════════════════════════════════

@router.get("/admin/users")
def get_all_users(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all users in the system"""
    from sqlalchemy import text

    users = db.execute(text("""
        SELECT id, name, email, role, created_at
        FROM users ORDER BY created_at DESC
    """)).fetchall()

    return {
        "users": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "joined": str(u.created_at)
            }
            for u in users
        ]
    }

@router.post("/admin/assign-doctor")
def assign_doctor(
    patient_id: int,
    doctor_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin assigns a doctor to a patient"""
    from sqlalchemy import text

    db.execute(text("""
        UPDATE patients
        SET assigned_doctor_id = :doctor_id
        WHERE user_id = :patient_id
    """), {"doctor_id": doctor_id, "patient_id": patient_id})
    db.commit()

    return {"message": "Doctor assigned successfully"}