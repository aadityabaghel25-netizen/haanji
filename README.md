# Haanji: a Hinglish voice helpline for small online sellers

**Built on Gnani AI: Prisma v3.0 speech-to-text and Timbre v3.0 text-to-speech.**
Entry for the Gnani AI Great Indian AI Internship Challenge, by Aaditya Baghel (solo).

A small Instagram or website seller gets the same five calls all day: *"mera parcel kahan hai?"*, *"mila hi nahi"*,
*"return karna hai"*, *"cancel kar do"*, *"galat size aaya"*. They come in Hinglish, on noisy phone lines, often while
the seller is packing orders. Missed calls become 1-star reviews, and an unanswered *"mila hi nahi"* can turn into a
chargeback a few weeks later.

Haanji answers those calls. The customer speaks Hinglish; Gnani transcribes it; Haanji's code answers **from the shop's
own order and courier records**; Gnani speaks the answer back in a natural Hinglish voice. Anything that would move money
(return, refund, cancel) becomes a ticket the seller approves with one click.

```
caller audio ──► Gnani Prisma v3.0 (REST, hi-IN + en-IN, transliterate) ──► "mera bedsheet abhi tak nahi mila"
                                                                               │
              shop records (orders, courier, delivery proof) ──► code: intent + order + answer + ticket?
                                                                               │
caller ear  ◄── Gnani Timbre v3.0 (voice Shivani, hi-en)  ◄──  "Courier ke record ke hisaab se aapka bedsheet 3 November deliver hua tha…"
```

## Why it's built this way

| Choice | Why |
|---|---|
| **Gnani Prisma v3.0 REST, `format=transliterate`** | About half a second per turn, and Hinglish comes back in Latin letters (*"mera order kahan hai"*), the way customers type it, so plain code can read it. |
| **`keyterms` and `topic`** | The shop's order numbers, product names and its own name are sent with every turn, so Gnani listens for *"bedsheet"*, *"dupatta"*, *"4821"*. |
| **Gnani Timbre v3.0, voice Shivani, `hi-en`** | A warm customer-care voice that speaks Hinglish naturally. The 10 sample callers use 10 other Timbre voices. |
| **No language model writes the answers** | A helpline that guesses a delivery date or promises a refund is worse than none. Every sentence Haanji says is built by code from a record, and the record is shown next to it. |
| **No money moves on a call** | Returns, cancels, refunds, address changes and complaints become tickets. Only the seller approves them, on the dashboard. |
| **Caller ID decides what may be said** | A known number hears its own orders by name. An unknown number gets tracking status only, never names, addresses or changes. Asking about someone else's order number gets nothing. |
| **"Not received" is caught early** | If the courier shows *delivered, OTP verified*, Haanji says so politely, and if the customer still wants to complain, the ticket is flagged as a **chargeback risk** with the proof and the call transcript attached. |

## Measured

[`docs/eval.md`](docs/eval.md): 48 labelled Hinglish and English caller sentences, each voiced by one of 10 Gnani voices,
transcribed by Gnani, then understood by Haanji's rules. Also run through a **simulated noisy phone line** (8 kHz,
300-3400 Hz, G.711 mu-law, noise at 10 dB SNR). The held-out set was written before the first run and never tuned on.

| Set | Text only (rules) | Gnani STT, clean audio | Gnani STT, noisy phone line |
|---|---|---|---|
| tune (20) | 100% | 100% | 95% |
| **held-out (28)** | **86%** | **82%** | **68%** |

Gnani speech-to-text took a **median 0.53 s per turn** (96 requests, slowest 0.74 s).

What the misses teach (all in [`docs/eval.md`](docs/eval.md)): most held-out misses are phrasings the rules don't know
yet (*"kya update hai"*, *"andar kuch aur hi tha"*), not hearing errors. The noisy line costs about 14 points, mostly
on short words (*radd* heard as *add*, *fata* as *pata*). A misunderstood turn fails safe: Haanji asks again, and after
two misses offers a callback from the seller. Both sets were written by us and voiced by TTS, so real calls will score lower.

## Try it

```bash
pip install -r requirements.txt
```
```bash
cp .env.example .env
```
Put your Gnani key in `.env` (`GNANI_API_KEY=`). Without a key, Haanji still runs: you type instead of speak.
```bash
python3 -m uvicorn haanji.main:app --port 8010
```
Open http://127.0.0.1:8010, pick a caller, press **Call**, then tap the mic and speak, or play the caller's sample lines.
Tick **Noisy phone line** to hear (and test) the same lines over a bad connection. The seller side is at `/seller`.

```bash
python3 -m unittest discover -s tests -v
```
```bash
python3 scripts/eval.py
```

## Files

| Path | What it does |
|---|---|
| `haanji/gnani.py` | Gnani STT (REST, Prisma v3.0) and TTS (Timbre), standard library only, one request at a time, retry on 429 |
| `haanji/brain.py` | Spoken numbers (*"chaar aath do ek"* → 4821), intent rules, the conversation, every reply, tickets |
| `haanji/shop.py` | The shop's records (made-up), dates said the way people say them (*kal*, *parson*, *12 November*) |
| `haanji/service.py` | A call = turns: audio → STT → brain → TTS; SQLite log of calls, turns and tickets |
| `haanji/audio.py` | The simulated phone line used by the demo toggle and the evaluation |
| `haanji/main.py`, `templates/`, `static/phone.js` | The helpline (a phone in the browser, mic recorded as 16 kHz WAV) and the seller dashboard |
| `evals/utterances.py`, `scripts/eval.py` | Labelled sentences and the measurement |

## Data and privacy

Everything is synthetic: the shop, the customers, the phone numbers (+91 90000 0000x), the orders and every voice
(Gnani TTS). No real person's voice or data is used. In a real deployment, call audio goes to Gnani for transcription and
only the transcript is kept, and callers are told at the start that they're talking to an AI assistant.

MIT licence.
