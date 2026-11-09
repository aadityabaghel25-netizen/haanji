# MEMORY.md: Haanji project facts, decisions, status

## Facts
- Builder: Aaditya Baghel, solo, registered for the Gnani challenge. Deadline 10 Nov 2026 11:59 PM IST.
- Made-up shop "Meera Handloom", Jaipur; 4 customers (+91 90000 0000x), 5 orders (4821–4825), dates relative to today.
- Sample caller lines in `data/samples.json`, voiced by Gnani Timbre v3.0 voices, cached in `data/cache/` (gitignored).

## Status
- **2026-11-09:** Built in one day. Helpline (browser phone, mic → 16 kHz WAV, sample callers, noisy-line toggle), seller
  dashboard (tickets, chargeback-risk flags, transcripts), 21 offline tests, live eval: held-out 86% text / 82% clean /
  68% phone line (10 dB), Gnani STT median 0.53 s.
- **Next:** public GitHub repo, 60-second demo video, LinkedIn/X post (needed before submitting), submission form.

## Decisions
| Date | Decision |
|---|---|
| 2026-11-09 | Separate project from DisputeDesk (Aaditya's call); idea = Hinglish voice helpline for small online sellers |
| 2026-11-09 | Rule-based understanding, code-written replies, no LLM: can't invent delivery dates or promise refunds |
| 2026-11-09 | Gnani STT REST (not batch) for ~0.5 s turns, `transliterate` for Latin Hinglish; agent voice Shivani (timbre-v3.0) |
| 2026-11-09 | Held-out eval run once and frozen; misses reported, not tuned away |
