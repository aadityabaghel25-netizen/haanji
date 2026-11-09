"""
Gnani AI speech APIs, called with the standard library only.

- stt():  Prisma v3.0 REST transcription. Clips up to 30 s, answers in about a second, and with format=transliterate
          writes Hinglish in Latin letters ("mera parcel kahan hai"), which is what the rest of Haanji reads.
- tts():  Timbre text-to-speech. Returns MP3 (or WAV) bytes.

Gnani allows one request at a time per account, so a lock serialises calls and a 429 is retried after a pause.
"""

import json
import threading
import time
import urllib.error
import urllib.request
import uuid

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
UA = "Haanji/0.1"
_lock = threading.Lock()


class GnaniError(Exception):
    pass


def _send(req: urllib.request.Request, timeout: int = 60) -> bytes:
    with _lock:
        for wait in (2, 5, 10, None):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read()
            except urllib.error.HTTPError as e:
                detail = e.read()[:300].decode("utf-8", "replace")
                if e.code != 429 or wait is None:
                    raise GnaniError(f"Gnani said no (HTTP {e.code}): {detail}") from None
                time.sleep(wait)
            except (urllib.error.URLError, TimeoutError) as e:
                raise GnaniError(f"Could not reach Gnani: {e}") from None
    raise GnaniError("Gnani is busy. Try again in a moment.")


def stt(api_key: str, audio: bytes, filename: str = "turn.wav", language: str = "hi-IN,en-IN",
        keyterms: list[str] | None = None, topic: str | None = None, model: str = "prisma-v3.0",
        output_format: str = "transliterate") -> dict:
    """Transcribe one short clip. Returns {"text", "latency_s", "raw"}."""
    fields = {"model": model, "language_code": language, "format": output_format}
    if keyterms:
        fields["keyterms"] = json.dumps(keyterms[:200], ensure_ascii=False)
    if topic:
        fields["topic"] = topic[:1600]
    boundary = uuid.uuid4().hex
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="audio_file"; filename="{filename}"\r\n'
                 "Content-Type: application/octet-stream\r\n\r\n".encode() + audio + b"\r\n")
    body = b"".join(parts) + f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(STT_URL, data=body, method="POST", headers={
        "User-Agent": UA, "X-API-Key-ID": api_key, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    start = time.time()
    data = json.loads(_send(req))
    if not data.get("success", True):
        raise GnaniError(f"Gnani couldn't transcribe this: {data}")
    return {"text": (data.get("transcript") or "").strip(), "latency_s": round(time.time() - start, 2), "raw": data}


def tts(api_key: str, text: str, voice: str = "Shivani", model: str = "timbre-v3.0", language: str = "hi-en",
        container: str = "mp3", sample_rate: int = 24000, speed: float = 1.0) -> bytes:
    """Speak `text`. The text is always written by Haanji's code from the shop's records, never by a model."""
    body = json.dumps({"text": text, "model": model, "voice": voice, "language": language, "speed": speed,
                       "audio_config": {"sample_rate": sample_rate, "num_channels": 1, "sample_width": 2, "encoding": "linear_pcm",
                                        "container": container, **({"bitrate": "64k"} if container == "mp3" else {})}}).encode()
    req = urllib.request.Request(TTS_URL, data=body, method="POST", headers={
        "User-Agent": UA, "X-API-Key-ID": api_key, "Content-Type": "application/json"})
    audio = _send(req)
    if not audio:
        raise GnaniError("Gnani returned no audio.")
    return audio
