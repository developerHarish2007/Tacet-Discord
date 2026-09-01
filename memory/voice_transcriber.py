import os
import re
import json
from typing import Tuple, Dict, Any, Optional

class VoiceTranscriber:
    """
    Multimodal Voice Knowledge Capture Engine.
    Transcribes senior technician voice notes using Whisper and structures them
    into clean diagnosis & fix steps using Gemma 4 LLM reasoning.
    """
    def __init__(self):
        self._whisper_model = None

    def _get_whisper_model(self):
        if self._whisper_model is None:
            try:
                import whisper
                print("Loading local Whisper model (tiny.en)...")
                self._whisper_model = whisper.load_model("tiny.en")
            except Exception as e:
                print(f"Whisper initialization note: {e}")
                self._whisper_model = False
        return self._whisper_model

    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribes audio file to text transcript"""
        if not audio_path or not os.path.exists(audio_path):
            return "No voice audio recorded."

        model = self._get_whisper_model()
        if model:
            try:
                res = model.transcribe(audio_path)
                text = res.get("text", "").strip()
                if text:
                    return text
            except Exception as e:
                print(f"Whisper transcription failed ({e}); checking fallback.")

        # SpeechRecognition fallback if whisper fails or non-wav format
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = r.record(source)
                return r.recognize_google(audio)
        except Exception:
            pass

        return f"Voice note captured from file '{os.path.basename(audio_path)}'"

    def process_senior_voice_note(
        self,
        audio_path: str,
        llm_engine: Optional[Any] = None
    ) -> Dict[str, str]:
        """
        Full pipeline: Audio -> Raw Transcript -> Gemma 4 Structured Cleaning -> Diagnosis & Fix Steps
        """
        raw_transcript = self.transcribe_audio(audio_path)
        
        confirmed_diagnosis = "Senior Voice Note Assessment"
        fix_steps = raw_transcript

        if llm_engine and raw_transcript and len(raw_transcript) > 10:
            prompt = (
                "You are an industrial expert AI. A senior technician recorded this voice note during shift handoff:\n"
                f"\"{raw_transcript}\"\n\n"
                "Extract and clean this voice note into two structured fields:\n"
                "1. CONFIRMED_DIAGNOSIS: A concise 1-sentence technical diagnosis.\n"
                "2. FIX_STEPS: Clear, numbered step-by-step resolution actions.\n"
                "Return ONLY valid JSON format:\n"
                "{\"confirmed_diagnosis\": \"...\", \"fix_steps\": \"...\"}"
            )
            try:
                raw_resp = llm_engine._call_llm_backend(
                    question="Process senior voice note",
                    evidence_text=prompt,
                    has_strong_match=False
                )
                json_match = re.search(r'\{.*\}', raw_resp, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    confirmed_diagnosis = parsed.get("confirmed_diagnosis", confirmed_diagnosis)
                    fix_steps = parsed.get("fix_steps", fix_steps)
            except Exception as e:
                print(f"Gemma 4 voice cleaning note: {e}")

        return {
            "raw_transcript": raw_transcript,
            "confirmed_diagnosis": confirmed_diagnosis,
            "fix_steps": fix_steps
        }
