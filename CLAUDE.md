# CLAUDE.md: instructions for any AI coding assistant working on Haanji

Read this, then `MEMORY.md`. Update `MEMORY.md` (Status, Decisions) at the end of every session.

## Who you are working with
- **Aaditya Baghel**: student, DevOps background (AWS, Terraform, K8s, Python), new to building AI apps. Explain AI ideas
  in plain words with a DevOps analogy. macOS, Python `python3`, Chrome, zsh.
- Terminal commands: **one per code block, one line each**. Never ask for secrets in chat; they live in `.env` only.

## Goal
Gnani AI "Great Indian AI Internship Challenge" (https://www.gnani.ai/internship). Deadline **10 Nov 2026, 11:59 PM IST**.
Entry = working app on Gnani's APIs + a public demo post on LinkedIn/X with #GnaniAI #GreatIndianAIInternshipChallenge
(post must be live before submitting) + written explanation + models used. Shortlist = verified engagement on the posts.
Separate from DisputeDesk (`~/Downloads/disputedesk-razorpay`, Razorpay entry): **don't change that project**.

## Golden rules
1. Every sentence Haanji speaks is built by code from the shop's records. No model writes answers.
2. No money moves on a call: returns, refunds, cancels, address changes become tickets the seller approves.
3. Unknown callers get tracking status only; never confirm another customer's order.
4. Synthetic data only (Gnani's rules: no real phone numbers, calls or IDs).
5. Offline mode (no key, typed turns) must keep working. Tests must pass: `python3 -m unittest discover -s tests -v`.
6. `evals/utterances.py` HOLDOUT is frozen: never change rules or labels because of a held-out result.

## Commands
```bash
python3 -m uvicorn haanji.main:app --port 8010   # http://127.0.0.1:8010 ; seller at /seller
python3 -m unittest discover -s tests -v
python3 scripts/eval.py                          # live Gnani eval (TTS + STT, clean + phone line) -> docs/eval.md
```

## Gnani facts (verified live 2026-11-09)
- STT REST: `POST https://api.vachana.ai/stt/v3` multipart `audio_file`, `model=prisma-v3.0`, `language_code=hi-IN,en-IN`,
  `format=transliterate` (Latin Hinglish), `keyterms` JSON array, `topic`. ≤30 s clips. ~0.5 s. Spoken numbers come back as
  English words ("four eight two one"), handled by `brain.digits_in`.
- TTS: `POST https://api.vachana.ai/api/v1/tts/inference`, `timbre-v3.0` voices (Shivani, Riyaa, Devansh, …) speak `hi-en`.
  WAV output has placeholder sizes in its header (`audio.fix_wav_header`). Header `X-API-Key-ID` + a `User-Agent`.
  One request at a time per account (429).
- python.org Python on macOS needs certifi for HTTPS (`config.use_certifi_if_needed`).
