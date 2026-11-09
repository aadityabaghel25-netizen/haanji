"""Web app: the helpline (a phone in the browser) and the seller's dashboard."""

import base64
import json
import os
import secrets

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from .audio import fix_wav_header, phone_line
from .config import PROJECT_ROOT, get_settings
from .gnani import GnaniError, tts
from .service import Service

settings = get_settings()
service = Service(settings)
templates = Jinja2Templates(directory=os.path.join(PROJECT_ROOT, "haanji", "templates"))
with open(os.path.join(PROJECT_ROOT, "data", "samples.json"), encoding="utf-8") as f:
    SAMPLES = json.load(f)["callers"]


class SellerAuth(BaseHTTPMiddleware):
    """The seller dashboard needs a password once SELLER_PASSWORD is set (always set it when the app is online)."""
    async def dispatch(self, request, call_next):
        if settings.seller_password and request.url.path.startswith("/seller"):
            auth = request.headers.get("authorization", "")
            ok = False
            if auth.startswith("Basic "):
                try:
                    _, _, pw = base64.b64decode(auth[6:]).decode().partition(":")
                    ok = secrets.compare_digest(pw, settings.seller_password)
                except Exception:
                    ok = False
            if not ok:
                return Response("Seller login needed", 401, {"WWW-Authenticate": 'Basic realm="Haanji seller"'})
        return await call_next(request)


async def helpline(request: Request):
    return templates.TemplateResponse(request, "helpline.html", {"shop": service.shop, "samples": SAMPLES, "voice": settings.voice_on,
                                                                 "agent_voice": settings.agent_voice, "tts_model": settings.tts_model,
                                                                 "stt_model": settings.stt_model})


async def seller(request: Request):
    return templates.TemplateResponse(request, "seller.html", {"shop": service.shop, "d": service.dashboard()})


async def summary_audio(request: Request):
    """The seller's spoken briefing. Text by code, voice by Gnani Timbre."""
    text = service.summary_text()
    if request.query_params.get("text") == "1" or not settings.voice_on:
        return JSONResponse({"text": text})
    try:
        key, _ = service.speak(text)
    except GnaniError as e:
        return JSONResponse({"error": str(e)}, 502)
    return JSONResponse({"text": text, "audio": f"/audio/{key}.mp3"})


async def decide(request: Request):
    form = await request.form()
    service.decide(int(request.path_params["ticket_id"]), form.get("action") == "approve")
    return RedirectResponse("/seller", 303)


async def reset(request: Request):
    service.reset()
    return RedirectResponse("/seller", 303)


async def api_call(request: Request):
    body = await request.json()
    try:
        return JSONResponse(service.start_call(str(body.get("phone", ""))))
    except GnaniError as e:
        return JSONResponse({"error": str(e)}, 502)


async def api_turn(request: Request):
    call_id = int(request.path_params["call_id"])
    form = await request.form()
    audio = form.get("audio")
    try:
        if audio is not None and hasattr(audio, "read"):
            data = await audio.read()
            if len(data) > 5_000_000:
                return JSONResponse({"error": "Keep each turn under 30 seconds."}, 400)
            return JSONResponse(service.turn(call_id, audio=data, filename=audio.filename or "turn.wav"))
        return JSONResponse(service.turn(call_id, text=str(form.get("text", ""))[:500]))
    except (GnaniError, ValueError) as e:
        return JSONResponse({"error": str(e)}, 400)


async def api_hangup(request: Request):
    service.end_call(int(request.path_params["call_id"]))
    return JSONResponse({"ok": True})


async def audio_file(request: Request):
    path = service.audio_path(request.path_params["key"])
    if not path:
        return Response("Not found", 404)
    return FileResponse(path, media_type="audio/mpeg")


async def sample_audio(request: Request):
    """A sample caller's line, voiced by Gnani TTS. ?phone=1 passes it through the simulated noisy phone line."""
    i, j = int(request.path_params["caller"]), int(request.path_params["line"])
    if not settings.voice_on or not (0 <= i < len(SAMPLES)) or not (0 <= j < len(SAMPLES[i]["lines"])):
        return Response("Not found", 404)
    noisy = request.query_params.get("phone") == "1"
    c = SAMPLES[i]
    path = os.path.join(service.cache_dir, f"sample_{i}_{j}_{c['voice']}{'_phone' if noisy else ''}.wav")
    if not os.path.exists(path):
        clean = os.path.join(service.cache_dir, f"sample_{i}_{j}_{c['voice']}.wav")
        if not os.path.exists(clean):
            try:
                wav = fix_wav_header(tts(settings.gnani_api_key, c["lines"][j], voice=c["voice"], model="timbre-v3.0",
                                         language="hi-en", container="wav", sample_rate=16000))
            except GnaniError as e:
                return Response(str(e), 502)
            with open(clean, "wb") as f:
                f.write(wav)
        if noisy:
            with open(clean, "rb") as f:
                data = phone_line(f.read(), snr_db=15)
            with open(path, "wb") as f:
                f.write(data)
    return FileResponse(path, media_type="audio/wav")


async def healthz(request: Request):
    return JSONResponse({"ok": True, "voice": settings.voice_on})


app = Starlette(routes=[
    Route("/", helpline),
    Route("/seller", seller),
    Route("/seller/tickets/{ticket_id:int}", decide, methods=["POST"]),
    Route("/seller/reset", reset, methods=["POST"]),
    Route("/seller/summary", summary_audio),
    Route("/api/call", api_call, methods=["POST"]),
    Route("/api/call/{call_id:int}/turn", api_turn, methods=["POST"]),
    Route("/api/call/{call_id:int}/hangup", api_hangup, methods=["POST"]),
    Route("/audio/{key}.mp3", audio_file),
    Route("/sample/{caller:int}/{line:int}.wav", sample_audio),
    Route("/healthz", healthz),
    Mount("/static", StaticFiles(directory=os.path.join(PROJECT_ROOT, "haanji", "static"))),
], middleware=[Middleware(SellerAuth)])
