import os
from dotenv import load_dotenv
from graph.orchestrator import medassist_graph

load_dotenv()

def resume_after_doctor_decision(
    thread_id: str,
    decision: str,
    edited_response: dict = None
) -> dict:
    """
    called when doctor approves, edits, or rejects.
    resumes the paused LangGraph graph from interrupt point.

    thread_id     — the conversation thread that was paused
    decision      — "approve", "edit", or "reject"
    edited_response — doctor's edited version if decision is "edit"
    """

    config = {"configurable": {"thread_id": thread_id}}

    if decision == "approve":
        # resume with original AI response unchanged
        resume_value = {
            "status": "approved",
            "approved_by": "doctor",
        }

    elif decision == "edit":
        # resume with doctor's edited response
        resume_value = {
            "status": "edited",
            "approved_by": "doctor",
            "edited_response": edited_response
        }

    elif decision == "reject":
        # resume with rejection — patient gets told
        # to contact doctor directly
        resume_value = {
            "status": "rejected",
            "message": "This response has been reviewed. "
                      "Please contact your doctor directly "
                      "for further guidance."
        }

    # resume the paused graph
    # this continues from exactly where interrupt() paused it
    result = medassist_graph.invoke(
        None,           # None = resume, don't start fresh
        config,
        resume=resume_value
    )

    return {
        "thread_id":      thread_id,
        "decision":       decision,
        "final_response": result.get("final_response"),
    }


# ── TEST ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("HITL module loaded successfully")
    print("Use resume_after_doctor_decision() to resume paused graphs")
    print("✅ hitl.py ready")