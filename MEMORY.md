# MEMORY.md: Haanji project facts, decisions, status

## Facts
- Builder: Aaditya Baghel, solo, registered for the Gnani challenge. Deadline 10 Nov 2026 11:59 PM IST.
- Made-up shop "Meera Handloom", Jaipur; 4 customers (+91 90000 0000x), 5 orders (4821–4825), dates relative to today.
- Sample caller lines in `data/samples.json`, voiced by Gnani Timbre v3.0 voices, cached in `data/cache/` (gitignored).

## Status
- **2026-11-09:** Built in one day. Helpline (browser phone, mic → 16 kHz WAV, sample callers, noisy-line toggle), seller
  dashboard (tickets, chargeback-risk flags, transcripts), 21 offline tests, live eval: held-out 86% text / 82% clean /
  68% phone line (10 dB), Gnani STT median 0.53 s.
- UI redesign: 3 columns (call setup + order on file, phone with live waveform and timer, conversation with Hear/Answer/Speak strip).
- Demo video `demo/haanji-demo.mp4` (59 s, gitignored), real call recorded with Playwright, audio rebuilt from the clips the page played.
- Public repo: https://github.com/aadityabaghel25-netizen/haanji (pushed 2026-11-09).
- Round 2 (09 Nov): shorter spoken replies (short item names), seller's spoken Hinglish summary (`/seller/summary`), redesigned seller dashboard, video re-recorded (59.5 s, opens with sourced data from docs/PROBLEM.md). Posting on X; Gnani's handle is @GnaniAi.
- 10 Nov: Gnani form needs a 1-page pitch (PITCH.md) and a 2–3 min demo: `demo/haanji-demo-full.mp4` (2:57, three calls). Unknown-caller sample now says "Order number 4 8 2 1" ("chaar aath do ek" was misheard by Gnani as "icar ath do ek").
- X post live 10 Nov 7:49 PM: https://x.com/Aadityacdc1/status/2120159501894758520 (60 s video, @GnaniAi tagged).
- **Next:** Drive link for the 2:57 video, then the Gnani form (previously: X post (needed before submitting), submission form. Answers in `docs/SUBMISSION.md`.

## Decisions
| Date | Decision |
|---|---|
| 2026-11-09 | Separate project from DisputeDesk (Aaditya's call); idea = Hinglish voice helpline for small online sellers |
| 2026-11-09 | Rule-based understanding, code-written replies, no LLM: can't invent delivery dates or promise refunds |
| 2026-11-09 | Gnani STT REST (not batch) for ~0.5 s turns, `transliterate` for Latin Hinglish; agent voice Shivani (timbre-v3.0) |
| 2026-11-09 | Held-out eval run once and frozen; misses reported, not tuned away |
