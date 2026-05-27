import os
import sys
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class LanguageProfile:
    code: str
    language_code: str
    name: str
    voice_name: str
    greeting: str


LANG_TABLE: dict[str, LanguageProfile] = {
    "1": LanguageProfile(
        code="1",
        language_code="en-US",
        name="English",
        voice_name="Aoede",
        greeting="Hello, you've reached SLT Mobitel. I'm Saru. How can I help today?",
    ),
    "2": LanguageProfile(
        code="2",
        language_code="si-LK",
        name="Sinhala",
        voice_name="Aoede",
        greeting=(
            "ආයුබෝවන්, මේක SLT මොබිටෙල්. මම සරු. අද ඔබට කොහොමද උදව් කරන්න පුළුවන්?"
        ),
    ),
    "3": LanguageProfile(
        code="3",
        language_code="ta-LK",
        name="Tamil",
        voice_name="Aoede",
        greeting=(
            "வணக்கம், SLT மொபிடெல்லுக்கு வரவேற்கிறோம். நான் சரு. "
            "இன்று உங்களுக்கு எப்படி உதவ முடியும்?"
        ),
    ),
}

LIVE_MODEL = os.environ.get("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")


def get_google_api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("ERROR: GOOGLE_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)
    return key


def get_mcp_server_url() -> str:
    return os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")


def pick_language() -> LanguageProfile:
    print("Select language for this call:")
    for code, profile in LANG_TABLE.items():
        print(f"  {code}. {profile.name}")
    choice = input("Choice [1/2/3]: ").strip()
    if choice not in LANG_TABLE:
        print(f"Invalid choice {choice!r}, defaulting to English.")
        choice = "1"
    return LANG_TABLE[choice]
