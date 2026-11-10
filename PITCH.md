# Haanji: a Hinglish voice helpline for small online sellers

**One-page solution pitch** · Gnani AI Great Indian AI Internship Challenge · Aaditya Baghel (solo) ·
Code: https://github.com/aadityabaghel25-netizen/haanji

## Problem
India's small online sellers (Instagram shops, D2C sites) get the same calls all day, in Hinglish, on noisy lines:
*"mera parcel kahan hai?"*, *"mila hi nahi"*, *"return karna hai"*. Customers want to call: **76%** of Indians prefer
calling a business (Truecaller × Tata Tele Business Services). But a one- or two-person shop can't answer:
**28–62%** of calls to small businesses go unanswered (CallRail, Invoca, 411 Locals). "Where is my order?" alone is
**20–50%** of e-commerce support contacts, and an unanswered *"mila hi nahi"* becomes a chargeback: **37%** of apparel
chargebacks are "not received" (Chargeflow). Sources and caveats: [`docs/PROBLEM.md`](docs/PROBLEM.md).

## Solution
Haanji picks up every call and talks Hinglish:

1. **Hear:** Gnani **Prisma v3.0** speech-to-text (REST, `hi-IN,en-IN`, `transliterate`), with the shop's order numbers and
   product names as `keyterms`. About **0.5 s** per turn, Hinglish back in Latin letters.
2. **Answer:** code works out the request (status, not received, return, cancel, damaged, address, human) and writes the
   reply **from the shop's own order and courier records**. No model writes answers, so Haanji can't invent a delivery
   date or promise a refund. The record is shown next to every answer.
3. **Speak:** Gnani **Timbre v3.0** (voice Shivani, `hi-en`) says it back naturally.
4. **Seller in control:** returns, cancels and complaints become tickets the seller approves with one click. The seller
   also hears a spoken Hinglish summary of the day.

**Safety by design:** caller ID decides what may be said (unknown numbers get tracking only, nobody can ask about someone
else's order); no money moves on a call; a *"mila hi nahi"* on a parcel the courier shows delivered with OTP is flagged
to the seller as a **chargeback risk**, with the proof and transcript attached.

## Measured
48 labelled Hinglish/English caller sentences, voiced by 10 Gnani voices, transcribed by Gnani, understood by Haanji.
Held-out set (28, written before the first run, never tuned on):

| Text only | Gnani STT, clean audio | Gnani STT, noisy 8 kHz phone line (10 dB) | Gnani STT time |
|---|---|---|---|
| 86% | **82%** | **68%** | median **0.53 s** per turn |

Misses fail safe: Haanji asks again, and after two misses offers a callback. Full results: [`docs/eval.md`](docs/eval.md).

## Why it's different
| Today | Haanji |
|---|---|
| Seller answers between packing orders, misses calls | Answers every call, instantly |
| Call centre / BPO: per-agent cost, built for big brands | No agents; the shop's order list is the only setup |
| IVR "press 1": can't take *"mera parcel kahan hai"* | Caller just talks, Hindi + English mixed |
| AI chatbots: may invent dates or promise refunds | Every sentence from a record; refunds wait for the seller |

## Next
Connect a real phone number (Exotel / Knowlarity), add Tamil and Bengali with Gnani's multilingual voices, Gnani
streaming STT for barge-in, and pilot with 10 Instagram sellers on consented, real calls to measure real accuracy.
