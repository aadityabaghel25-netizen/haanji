"""Settings from .env. No Gnani key = offline mode: the helpline still works with typed questions (no voice)."""

import os
from dataclasses import dataclass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env() -> None:
    path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    use_certifi_if_needed()


def use_certifi_if_needed() -> None:
    """python.org Python on macOS ships without trusted certificates, so HTTPS fails with
    CERTIFICATE_VERIFY_FAILED. If certifi is installed, point Python at its bundle."""
    if os.environ.get("SSL_CERT_FILE"):
        return
    try:
        import certifi
    except ImportError:
        return
    os.environ["SSL_CERT_FILE"] = certifi.where()


@dataclass
class Settings:
    gnani_api_key: str
    stt_model: str
    stt_language: str
    tts_model: str
    agent_voice: str
    tts_language: str
    shop_path: str
    database_path: str
    seller_password: str

    @property
    def voice_on(self) -> bool:
        return bool(self.gnani_api_key)


def get_settings() -> Settings:
    load_env()
    e = os.environ.get
    return Settings(
        gnani_api_key=e("GNANI_API_KEY", ""),
        stt_model=e("GNANI_STT_MODEL", "prisma-v3.0"),
        stt_language=e("GNANI_STT_LANGUAGE", "hi-IN,en-IN"),
        tts_model=e("GNANI_TTS_MODEL", "timbre-v3.0"),
        agent_voice=e("GNANI_AGENT_VOICE", "Shivani"),
        tts_language=e("GNANI_TTS_LANGUAGE", "hi-en"),
        shop_path=e("SHOP_PATH", os.path.join(PROJECT_ROOT, "data", "shop.json")),
        database_path=e("DATABASE_PATH", os.path.join(PROJECT_ROOT, "data", "haanji.db")),
        seller_password=e("SELLER_PASSWORD", ""),
    )
