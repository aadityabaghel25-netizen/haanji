"""
How well does Haanji understand callers? Measured three ways on labelled Hinglish utterances:

  1. text      the rules alone, on the typed sentence (the ceiling)
  2. clean     Gnani Timbre voices the sentence (10 different voices), Gnani Prisma v3.0 transcribes it, then the rules
  3. phone     the same audio through a simulated phone line first (8 kHz, 300-3400 Hz, mu-law, noise at 10 dB SNR)

A turn counts as right when the intent is right and, if the caller said an order number, that number was picked up.

    python3 scripts/eval.py            # tune and held-out sets, writes docs/eval.md and docs/eval.json
    python3 scripts/eval.py --text     # text only, no Gnani calls

Uses Gnani credit: one TTS and two STT calls per utterance (about 48 utterances).
"""

import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from evals.utterances import HOLDOUT, TUNE, VOICES  # noqa: E402
from haanji.audio import fix_wav_header, phone_line  # noqa: E402
from haanji.brain import understand  # noqa: E402
from haanji.config import get_settings  # noqa: E402
from haanji.gnani import stt, tts  # noqa: E402
from haanji.shop import Shop  # noqa: E402

SNR = 10


def correct(text: str, intent: str, order: str | None, shop: Shop) -> tuple[bool, str, list[str]]:
    u = understand(text, shop)
    return u.intent == intent and (order is None or order in u.order_ids), u.intent, u.order_ids


def run(split: str, items, shop: Shop, s, voice_on: bool) -> list[dict]:
    rows = []
    cache = os.path.join(ROOT, "data", "cache", "eval")
    os.makedirs(cache, exist_ok=True)
    for n, (text, intent, order) in enumerate(items):
        row = {"split": split, "text": text, "intent": intent, "order": order}
        row["text_ok"], row["text_got"], _ = correct(text, intent, order, shop)
        if voice_on:
            voice = VOICES[n % len(VOICES)]
            path = os.path.join(cache, f"{split}_{n}_{voice}.wav")
            if not os.path.exists(path):
                with open(path, "wb") as f:
                    f.write(fix_wav_header(tts(s.gnani_api_key, text, voice=voice, model="timbre-v3.0", language="hi-en",
                                               container="wav", sample_rate=16000)))
            with open(path, "rb") as f:
                clean = f.read()
            row["voice"] = voice
            for cond, audio in (("clean", clean), ("phone", phone_line(clean, SNR, seed=n))):
                r = stt(s.gnani_api_key, audio, f"{split}_{n}.wav", language=s.stt_language, keyterms=shop.keyterms(),
                        topic=f"Customer calling {shop.name}, an online clothing shop, about an order", model=s.stt_model)
                ok, got, orders = correct(r["text"], intent, order, shop)
                row[cond] = {"heard": r["text"], "ok": ok, "got": got, "orders": orders, "latency_s": r["latency_s"]}
        rows.append(row)
        print(f"{split:8s} {n:2d} text={'✓' if row['text_ok'] else '✗'}"
              + (f" clean={'✓' if row['clean']['ok'] else '✗'} phone={'✓' if row['phone']['ok'] else '✗'}" if voice_on else "")
              + f"  {text}", flush=True)
    return rows


def pct(rows, key) -> str:
    vals = [r[key]["ok"] if isinstance(r.get(key), dict) else r[key] for r in rows if key in r]
    return f"{sum(vals)}/{len(vals)} ({100 * sum(vals) / len(vals):.0f}%)" if vals else "–"


def main() -> int:
    s = get_settings()
    voice_on = s.voice_on and "--text" not in sys.argv
    shop = Shop(os.path.join(ROOT, "data", "shop.json"))
    rows = run("tune", TUNE, shop, s, voice_on) + run("holdout", HOLDOUT, shop, s, voice_on)
    lat = sorted(r[c]["latency_s"] for r in rows for c in ("clean", "phone") if c in r)
    lines = ["# Haanji evaluation", "",
             f"Run {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · STT `{s.stt_model}` (`{s.stt_language}`, transliterate) · "
             f"voices: Gnani `timbre-v3.0` ({len(VOICES)} voices, `hi-en`) · phone line: 8 kHz, 300-3400 Hz, mu-law, {SNR} dB SNR", "",
             "A turn is right when the intent is right and any order number the caller said was picked up. "
             "The held-out set was written before the first run and is never tuned on. Both sets were written by us, "
             "and voiced by text-to-speech, so they are cleaner than real customers on real phones.", "",
             "| Set | Utterances | Text only (rules) | Gnani STT, clean audio | Gnani STT, noisy phone line |",
             "|---|---|---|---|---|"]
    for split in ("tune", "holdout"):
        rs = [r for r in rows if r["split"] == split]
        lines.append(f"| {split} | {len(rs)} | {pct(rs, 'text_ok')} | {pct(rs, 'clean')} | {pct(rs, 'phone')} |")
    if lat:
        lines += ["", f"Gnani STT time per turn: median **{lat[len(lat) // 2]:.2f} s**, slowest {lat[-1]:.2f} s ({len(lat)} requests)."]
    misses = [r for r in rows if r["split"] == "holdout" and not (r["text_ok"] and r.get("clean", {}).get("ok", True) and r.get("phone", {}).get("ok", True))]
    if misses:
        lines += ["", "## Held-out misses", "", "| Said | Want | Text | Heard (clean) | Heard (phone) |", "|---|---|---|---|---|"]
        for r in misses:
            cell = lambda c: (f"{'✓' if r[c]['ok'] else '✗ ' + r[c]['got']} · {r[c]['heard']}" if c in r else "–")
            lines.append(f"| {r['text']} | {r['intent']}{' ' + r['order'] if r['order'] else ''} | {'✓' if r['text_ok'] else '✗ ' + r['text_got']} | {cell('clean')} | {cell('phone')} |")
    out = "\n".join(lines) + "\n"
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    with open(os.path.join(ROOT, "docs", "eval.md"), "w", encoding="utf-8") as f:
        f.write(out)
    with open(os.path.join(ROOT, "docs", "eval.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print("\n" + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
