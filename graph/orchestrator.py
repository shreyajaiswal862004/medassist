import os
from typing import TypedDict, Optional
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from agents.classifier import classify_input, InputType
from agents.text_agent import process_text
from agents.vision_agent import process_image
from agents.lab_agent import analyse_lab_values
from agents.voice_agent import process_voice
from agents.safety import validate_input, apply_safety
from utils.pdf_parser import process_pdf

load_dotenv()

# ── STATE ────────────────────────────────────────────────────
# this dictionary flows through every node
# each node reads from it and writes to it
class MedAssistState(TypedDict):
    # inputs
    user_id:        int
    text_input:     Optional[str]
    file_path:      Optional[str]
    structured_data: Optional[dict]
    chat_history:   list

    # set by classifier
    input_type:     Optional[str]

    # set by processing agents
    agent_output:   Optional[dict]

    # set by safety node
    safe_response:  Optional[dict]
    needs_review:   bool
    is_emergency:   bool

    # set by hitl node
    final_response: Optional[dict]

    # errors
    error:          Optional[str]

# ── NODE 1: VALIDATE INPUT ───────────────────────────────────
def validate_node(state: MedAssistState) -> dict:
    """
    first node — validates the input before anything else.
    checks for empty input, too long, prompt injection.
    if invalid → sets error and skips to end.
    """
    print("NODE: validate")

    text = state.get("text_input")

    if text:
        validation = validate_input(text)
        if not validation.is_valid:
            return {"error": validation.error}
        # use cleaned version
        return {"text_input": validation.cleaned_input}

    return {}

# ── NODE 2: CLASSIFY INPUT ───────────────────────────────────
def classify_node(state: MedAssistState) -> dict:
    """
    second node — detects what type of input this is.
    sets input_type which the conditional edge uses
    to route to the correct agent.
    """
    print("NODE: classify")

    input_type = classify_input(
        file_path=state.get("file_path"),
        text_input=state.get("text_input"),
        structured_data=state.get("structured_data")
    )

    print(f"  Detected: {input_type}")
    return {"input_type": input_type}

# ── ROUTING FUNCTION ─────────────────────────────────────────
def route_to_agent(state: MedAssistState) -> str:
    """
    conditional edge function.
    reads input_type from state and returns
    which node to go to next.
    """
    input_type = state.get("input_type")

    if state.get("error"):
        return "error_node"

    routing = {
        InputType.TEXT:                "text_agent_node",
        InputType.MEDICAL_REPORT_TEXT: "text_agent_node",
        InputType.PRESCRIPTION:        "vision_agent_node",
        InputType.XRAY:                "vision_agent_node",
        InputType.CT_SCAN:             "vision_agent_node",
        InputType.MRI:                 "vision_agent_node",
        InputType.SONOGRAPHY:          "vision_agent_node",
        InputType.BONE_SCAN:           "vision_agent_node",
        InputType.PDF_DIGITAL:         "pdf_agent_node",
        InputType.PDF_SCANNED:         "pdf_agent_node",
        InputType.PDF_MIXED:           "pdf_agent_node",
        InputType.LAB_VALUES:          "lab_agent_node",
        InputType.SENSOR_DATA:         "lab_agent_node",
        InputType.VOICE:               "voice_agent_node",
    }

    return routing.get(input_type, "text_agent_node")

# ── NODE 3A: TEXT AGENT ──────────────────────────────────────
def text_agent_node(state: MedAssistState) -> dict:
    print("NODE: text_agent")
    result = process_text(
        state.get("text_input", ""),
        state.get("chat_history", [])
    )
    return {"agent_output": result}

# ── NODE 3B: VISION AGENT ────────────────────────────────────
def vision_agent_node(state: MedAssistState) -> dict:
    print("NODE: vision_agent")
    input_type = state.get("input_type", "unknown")
    result = process_image(
        state.get("file_path"),
        image_type=input_type
    )
    return {"agent_output": result}

# ── NODE 3C: PDF AGENT ───────────────────────────────────────
def pdf_agent_node(state: MedAssistState) -> dict:
    print("NODE: pdf_agent")
    result = process_pdf(state.get("file_path"))
    return {"agent_output": result}

# ── NODE 3D: LAB AGENT ───────────────────────────────────────
def lab_agent_node(state: MedAssistState) -> dict:
    print("NODE: lab_agent")

    # lab values can come as structured_data or text
    if state.get("structured_data"):
        result = analyse_lab_values(state["structured_data"])
    else:
        # parse from text — extract key:value pairs
        import re
        text = state.get("text_input", "")
        lab_dict = {}
        # simple pattern: "HbA1c: 9.2%" or "HbA1c = 9.2%"
        pattern = r"([\w\s]+)[:=]\s*([\d.]+\s*[\w/%µ]*)"
        for match in re.finditer(pattern, text):
            key = match.group(1).strip()
            value = match.group(2).strip()
            lab_dict[key] = value
        result = analyse_lab_values(lab_dict)

    return {"agent_output": result}

# ── NODE 3E: VOICE AGENT ─────────────────────────────────────
def voice_agent_node(state: MedAssistState) -> dict:
    print("NODE: voice_agent")
    result = process_voice(
        state.get("file_path"),
        state.get("chat_history", [])
    )
    return {"agent_output": result}

# ── NODE 3F: ERROR NODE ──────────────────────────────────────
def error_node(state: MedAssistState) -> dict:
    print("NODE: error")
    return {
        "final_response": {
            "error": state.get("error", "Unknown error"),
            "status": "failed"
        }
    }

# ── NODE 4: SAFETY NODE ──────────────────────────────────────
def safety_node(state: MedAssistState) -> dict:
    """
    runs after every agent.
    applies safety wrapper:
    - emergency check
    - disclaimer injection
    - confidence check
    """
    print("NODE: safety")

    agent_output = state.get("agent_output", {})

    # get the response data from agent output
    response_data = agent_output.get("response") or agent_output.get("data") or {}

    # apply safety wrapper
    safe = apply_safety(
        user_input=state.get("text_input", ""),
        ai_response=response_data
    )

    # check if needs review
    needs_review = (
        agent_output.get("needs_review", False) or
        safe.get("needs_review", False)
    )

    is_emergency = (
        agent_output.get("is_emergency", False) or
        safe.get("is_emergency", False)
    )

    return {
        "safe_response": safe,
        "needs_review": needs_review,
        "is_emergency": is_emergency
    }

# ── HITL ROUTING ─────────────────────────────────────────────
def route_after_safety(state: MedAssistState) -> str:
    """
    after safety check — decide:
    needs_review=True → pause for doctor (hitl_node)
    needs_review=False → send directly (respond_node)
    """
    if state.get("needs_review"):
        return "hitl_node"
    return "respond_node"

# ── NODE 5A: HITL NODE ───────────────────────────────────────
def hitl_node(state: MedAssistState) -> dict:
    """
    pauses the graph and waits for doctor review.
    interrupt() freezes execution here.
    when doctor approves via API, graph resumes.
    """
    print("NODE: hitl — pausing for doctor review")

    # interrupt() pauses graph here
    # sends the safe_response to the doctor
    # doctor sees it in their review queue
    # when doctor approves, the approved response
    # comes back as the return value of interrupt()
    doctor_decision = interrupt({
        "message": "AI output requires doctor review",
        "ai_response": state.get("safe_response"),
        "user_id": state.get("user_id"),
        "is_emergency": state.get("is_emergency")
    })

    # doctor_decision contains what the doctor approved
    # could be original response or edited version
    return {"final_response": doctor_decision}

# ── NODE 5B: RESPOND NODE ────────────────────────────────────
def respond_node(state: MedAssistState) -> dict:
    """
    high confidence — no review needed.
    sends safe_response directly as final response.
    """
    print("NODE: respond — sending directly to patient")
    return {"final_response": state.get("safe_response")}

# ── BUILD THE GRAPH ──────────────────────────────────────────
def build_graph():
    """
    assembles all nodes and edges into the complete graph.
    """
    # memory saver stores graph state between interrupts
    # this is what allows HITL to pause and resume
    memory = MemorySaver()

    # create the graph with our state definition
    graph = StateGraph(MedAssistState)

    # ── ADD ALL NODES ──
    graph.add_node("validate_node",      validate_node)
    graph.add_node("classify_node",      classify_node)
    graph.add_node("text_agent_node",    text_agent_node)
    graph.add_node("vision_agent_node",  vision_agent_node)
    graph.add_node("pdf_agent_node",     pdf_agent_node)
    graph.add_node("lab_agent_node",     lab_agent_node)
    graph.add_node("voice_agent_node",   voice_agent_node)
    graph.add_node("error_node",         error_node)
    graph.add_node("safety_node",        safety_node)
    graph.add_node("hitl_node",          hitl_node)
    graph.add_node("respond_node",       respond_node)

    # ── ADD EDGES ──
    # START → validate → classify
    graph.add_edge(START, "validate_node")
    graph.add_edge("validate_node", "classify_node")

    # classify → conditional → correct agent
    graph.add_conditional_edges(
        "classify_node",
        route_to_agent,
        {
            "text_agent_node":   "text_agent_node",
            "vision_agent_node": "vision_agent_node",
            "pdf_agent_node":    "pdf_agent_node",
            "lab_agent_node":    "lab_agent_node",
            "voice_agent_node":  "voice_agent_node",
            "error_node":        "error_node",
        }
    )

    # all agents → safety
    graph.add_edge("text_agent_node",   "safety_node")
    graph.add_edge("vision_agent_node", "safety_node")
    graph.add_edge("pdf_agent_node",    "safety_node")
    graph.add_edge("lab_agent_node",    "safety_node")
    graph.add_edge("voice_agent_node",  "safety_node")

    # safety → conditional → hitl or respond
    graph.add_conditional_edges(
        "safety_node",
        route_after_safety,
        {
            "hitl_node":    "hitl_node",
            "respond_node": "respond_node",
        }
    )

    # both end at END
    graph.add_edge("hitl_node",    END)
    graph.add_edge("respond_node", END)
    graph.add_edge("error_node",   END)

    # compile with memory for HITL support
    return graph.compile(checkpointer=memory)

# ── CREATE GRAPH INSTANCE ────────────────────────────────────
# this is what routes.py will import and use
medassist_graph = build_graph()

# ── RUN THE GRAPH ────────────────────────────────────────────
def run_graph(
    user_id: int,
    text_input: str = None,
    file_path: str = None,
    structured_data: dict = None,
    chat_history: list = [],
    thread_id: str = None
) -> dict:
    """
    main function to run the graph.
    call this from routes.py instead of calling
    agents directly.
    """
    import uuid

    # each conversation needs a unique thread_id
    # this is how LangGraph tracks state between
    # multiple turns of the same conversation
    if not thread_id:
        thread_id = str(uuid.uuid4())

    # config tells LangGraph which thread this belongs to
    config = {"configurable": {"thread_id": thread_id}}

    # initial state
    initial_state = {
        "user_id":        user_id,
        "text_input":     text_input,
        "file_path":      file_path,
        "structured_data": structured_data,
        "chat_history":   chat_history,
        "input_type":     None,
        "agent_output":   None,
        "safe_response":  None,
        "needs_review":   False,
        "is_emergency":   False,
        "final_response": None,
        "error":          None,
    }

    # run the graph
    result = medassist_graph.invoke(initial_state, config)

    return {
        "thread_id":      thread_id,
        "final_response": result.get("final_response"),
        "needs_review":   result.get("needs_review"),
        "is_emergency":   result.get("is_emergency"),
        "input_type":     result.get("input_type"),
    }


# ── TEST ─────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n--- TEST 1: text symptom through full graph ---")
    result = run_graph(
        user_id=1,
        text_input="I have fever and headache since 2 days"
    )
    print("Input type:", result["input_type"])
    print("Is emergency:", result["is_emergency"])
    print("Needs review:", result["needs_review"])
    print("Response:", result["final_response"])

    print("\n--- TEST 2: emergency symptom ---")
    result = run_graph(
        user_id=1,
        text_input="I have severe chest pain and cannot breathe"
    )
    print("Is emergency:", result["is_emergency"])
    print("Alert:", result["final_response"].get("emergency_alert"))

    print("\n--- TEST 3: lab values ---")
    result = run_graph(
        user_id=1,
        structured_data={
            "HbA1c": "9.2%",
            "fasting_glucose": "210 mg/dL",
            "haemoglobin": "9.2 g/dL"
        }
    )
    print("Input type:", result["input_type"])
    print("Needs review:", result["needs_review"])

    print("\n✅ orchestrator working")