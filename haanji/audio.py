"""Audio helpers: a simulated phone line, so we can test how Gnani does on telephony-quality audio."""

import io
import wave


def phone_line(wav_bytes: bytes, snr_db: float = 15, seed: int = 7) -> bytes:
    """A rough telephone channel: 300-3400 Hz band, 8 kHz, background noise at `snr_db` (over the whole clip),
    then G.711 mu-law encode and decode. Input: a 16-bit mono WAV at any rate. Output: an 8 kHz 16-bit mono WAV."""
    import numpy as np
    with wave.open(io.BytesIO(wav_bytes)) as r:
        rate = r.getframerate()
        x = np.frombuffer(r.readframes(r.getnframes()), dtype="<i2").astype(np.float64) / 32768
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / rate)
    spec[(freqs < 300) | (freqs > 3400)] = 0
    x = np.fft.irfft(spec, len(x))
    n_out = int(len(x) * 8000 / rate)
    y = np.interp(np.linspace(0, len(x) - 1, n_out), np.arange(len(x)), x)       # resample to 8 kHz
    noise = np.random.default_rng(seed).normal(size=len(y))
    nspec = np.fft.rfft(noise)
    nspec[np.fft.rfftfreq(len(noise), 1 / 8000) < 300] = 0
    noise = np.fft.irfft(nspec, len(noise))
    noise *= np.sqrt(np.mean(y ** 2) / np.mean(noise ** 2)) / (10 ** (snr_db / 20))
    y = np.clip(y + noise, -1, 1)
    mu = 255.0
    q = np.round((np.sign(y) * np.log1p(mu * np.abs(y)) / np.log1p(mu) + 1) / 2 * 255) / 255 * 2 - 1
    y = np.sign(q) * np.expm1(np.abs(q) * np.log1p(mu)) / mu
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
    return out.getvalue()


def fix_wav_header(wav_bytes: bytes) -> bytes:
    """Gnani's streamed WAV has placeholder sizes in its header; rewrite them so every player and library reads it."""
    i = wav_bytes.find(b"data")
    if i < 0:
        return wav_bytes
    data = wav_bytes[i + 8:]
    fmt = wav_bytes[:i]
    head = bytearray(fmt + b"data" + len(data).to_bytes(4, "little"))
    head[4:8] = (len(head) - 8 + len(data)).to_bytes(4, "little")
    return bytes(head) + data
