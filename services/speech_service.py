"""Voice + multilingual pipeline: Speech-to-Text -> Translation -> Intent -> Report.

Speech-to-Text and Text-to-Speech run in the browser (Web Speech API) in this
prototype; server-side Cloud Speech can be plugged in here. Translation uses
the Cloud Translation v2 REST API when GOOGLE_TRANSLATE_API_KEY is set,
otherwise text passes through untranslated with a DEMO note.
"""
import logging

import requests

from .config import cfg, is_configured

log = logging.getLogger("airwatch")

LANGUAGES = [
    ("en", "English", "en-IN"), ("hi", "Hindi", "hi-IN"), ("gu", "Gujarati", "gu-IN"),
    ("mr", "Marathi", "mr-IN"), ("bn", "Bengali", "bn-IN"), ("ta", "Tamil", "ta-IN"),
    ("te", "Telugu", "te-IN"), ("kn", "Kannada", "kn-IN"), ("ml", "Malayalam", "ml-IN"),
]

# Multilingual keyword intent detection (Dialogflow-ready fallback)
INTENT_KEYWORDS = {
    "crop_burning": ["crop", "stubble", "farm", "field", "parali", "पराली", "खेत", "ખેતર", "પરાળ", "शेत"],
    "industrial": ["factory", "industry", "industrial", "chimney", "stack", "फैक्ट्री", "कारखाना", "ફેક્ટરી", "કારખાનું", "चिमनी"],
    "garbage_burning": ["garbage", "waste", "trash", "plastic", "कचरा", "કચરો", "कूड़ा"],
    "dust": ["dust", "construction", "road", "धूल", "ધૂળ", "धूळ"],
    "smoke": ["smoke", "fire", "burning", "धुआं", "धुआँ", "आग", "ધુમાડો", "આગ", "धूर"],
}


def translate(text: str, target: str = "en", source: str | None = None) -> dict:
    if not text:
        return {"text": "", "mode": "NONE"}
    if source == target:
        return {"text": text, "mode": "NOT_REQUIRED"}
    if is_configured("GOOGLE_TRANSLATE_API_KEY"):
        try:
            payload = {"q": text, "target": target, "format": "text"}
            if source:
                payload["source"] = source
            r = requests.post(
                "https://translation.googleapis.com/language/translate/v2",
                params={"key": cfg("GOOGLE_TRANSLATE_API_KEY")}, data=payload, timeout=15,
            )
            r.raise_for_status()
            return {"text": r.json()["data"]["translations"][0]["translatedText"], "mode": "LIVE"}
        except Exception as exc:
            log.warning("Translation failed: %s", exc)
    return {"text": text, "mode": "DEMO (translation API not configured — original text kept)"}


def detect_intent(text: str) -> dict:
    t = (text or "").lower()
    scores = {k: sum(1 for w in words if w.lower() in t) for k, words in INTENT_KEYWORDS.items()}
    best = max(scores, key=scores.get) if any(scores.values()) else "unknown"
    return {"intent": "report_pollution", "pollution_type": best, "matched": scores.get(best, 0)}


def process_voice_report(transcript: str, language: str) -> dict:
    translated = translate(transcript, "en", language)
    intent = detect_intent(transcript + " " + translated["text"])
    return {
        "transcript": transcript,
        "language": language,
        "translated": translated["text"],
        "translation_mode": translated["mode"],
        "intent": intent,
        "pipeline": ["Speech-to-Text", "Translation", "Intent detection", "Pollution report", "Location confirmation"],
    }
