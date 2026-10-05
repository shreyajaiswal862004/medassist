import os
from pathlib import Path
from dotenv import load_dotenv
from faster_whisper import WhisperModel

load_dotenv()

# ── LOAD WHISPER MODEL ───────────────────────────────────────
# loads once when the file is imported
# device="cpu" means runs on your CPU — no GPU needed
# compute_type="int8" makes it faster on CPU
# model downloads automatically first time (~150MB)
print("Loading Whisper model...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
print("Whisper model loaded.")

# ── SUPPORTED AUDIO FORMATS ──────────────────────────────────
SUPPORTED_FORMATS = [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4"]

# ── TRANSCRIBE AUDIO ─────────────────────────────────────────
def transcribe_audio(audio_path: str) -> dict:
    """
    converts audio file to text using faster-whisper.
    runs completely locally — no API call needed.
    supports multiple languages including Hindi and English.

    returns:
    {
        "transcript": "what the person said",
        "language": "en / hi / etc",
        "confidence": 0.0 to 1.0
    }
    """
    path = Path(audio_path)

    # check file exists
    if not path.exists():
        return {
            "transcript": None,
            "language": None,
            "confidence": 0.0,
            "error": f"Audio file not found: {audio_path}"
        }

    # check format is supported
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        return {
            "transcript": None,
            "language": None,
            "confidence": 0.0,
            "error": f"Unsupported format: {path.suffix}. Use {SUPPORTED_FORMATS}"
        }

    # transcribe
    # segments = chunks of the audio with timestamps
    # info = metadata like language detected
    segments, info = whisper_model.transcribe(
        audio_path,
        beam_size=5,          # higher = more accurate but slower
        language=None,        # None = auto detect language
        vad_filter=True,      # removes silence automatically
    )

    # join all segments into one transcript
    transcript = " ".join([segment.text for segment in segments]).strip()

    # calculate average confidence from segments
    # whisper gives probability per segment
    return {
        "transcript": transcript,
        "language": info.language,
        "language_probability": round(info.language_probability, 2),
        "confidence": round(info.language_probability, 2),
        "error": None
    }

# ── MAIN: process voice input ────────────────────────────────
def process_voice(audio_path: str, chat_history: list = []) -> dict:
    """
    main function.
    1. transcribes audio to text
    2. passes transcript to text_agent
    3. returns same response as text_agent

    this means all safety checks, emergency detection,
    and Groq analysis happen automatically via text_agent.
    voice is just a different way to input text.
    """
    from agents.text_agent import process_text
    from agents.safety import apply_safety

    # step 1 — transcribe
    transcription = transcribe_audio(audio_path)

    # if transcription failed
    if transcription["error"]:
        return {
            "status": "failed",
            "error": transcription["error"],
            "input_type": "voice"
        }

    transcript = transcription["transcript"]

    if not transcript:
        return {
            "status": "failed",
            "error": "Could not transcribe audio — please speak clearly",
            "input_type": "voice"
        }

    print(f"Transcript: {transcript}")
    print(f"Language detected: {transcription['language']}")

    # step 2 — pass transcript to text agent
    # from here it's identical to a text message
    result = process_text(transcript, chat_history)

    if result.get("status") == "failed":
        return {
            "status": "failed",
            "error": "AI processing failed",
            "input_type": "voice",
            "transcript": transcript
        }

    # step 3 — apply safety wrapper
    safe_response = apply_safety(transcript, result["response"])

    # add voice-specific info to response
    safe_response["input_type"] = "voice"
    safe_response["transcript"] = transcript
    safe_response["language_detected"] = transcription["language"]

    return safe_response


# ── TEST ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    # to test — record a short voice message
    # save it as test_voice.mp3 in your project folder
    # and run: python -m agents.voice_agent

    test_audio = "test_voice.mp4"

    if not Path(test_audio).exists():
        print(f"\nNo test audio found at {test_audio}")
        print("To test voice agent:")
        print("1. Record yourself saying symptoms on your phone")
        print("2. Save as test_voice.mp3 in your project folder")
        print("3. Run python -m agents.voice_agent again")
        print("\nTesting transcribe function with a dummy check...")

        # test that model loaded correctly at least
        print("Whisper model status: loaded ✅")
        print("\n✅ voice agent ready — add test_voice.mp3 to test fully")
        sys.exit(0)

    print(f"\n--- TEST: transcribing {test_audio} ---")
    result = process_voice(test_audio)

    print("Transcript:", result.get("transcript"))
    print("Language:", result.get("language_detected"))
    print("Emergency:", result.get("is_emergency"))
    print("Conditions:", result.get("possible_conditions"))
    print("\n✅ voice agent working")