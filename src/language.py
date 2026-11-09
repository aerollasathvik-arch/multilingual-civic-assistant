"""Detect which supported language a question is written in.

Uses lingua (Apache-2.0), restricted to the five project languages, which makes
short questions much easier to classify than open-set detection. Arabic and Urdu
share a script, so restricting the set matters most for those two.
"""
from lingua import Language, LanguageDetectorBuilder

SUPPORTED = {
    Language.ENGLISH: "en", Language.POLISH: "pl", Language.ROMANIAN: "ro",
    Language.ARABIC: "ar", Language.URDU: "ur",
}
_detector = LanguageDetectorBuilder.from_languages(*SUPPORTED).build()


def detect(text):
    """Return 'en', 'pl', 'ro', 'ar' or 'ur'; falls back to 'en' if lingua cannot decide."""
    lang = _detector.detect_language_of(text)
    return SUPPORTED.get(lang, "en")
