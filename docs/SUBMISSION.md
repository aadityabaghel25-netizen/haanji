# Gnani AI Great Indian AI Internship Challenge: submission draft

Deadline: **10 Nov 2026, 11:59 PM IST.** Order of steps: push the repo → post the demo on LinkedIn (and X) → submit the
form with the post links. The post must be live before you submit. Shortlisting is by verified engagement on the
nominated posts, so post as early as you can.

Demo video: `demo/haanji-demo.mp4` (59 s, 1080p). Upload it to the post directly (native video gets more reach than a link).

## Project details

**Project title:** Haanji: a Hinglish voice helpline for small online sellers

**The problem you are solving:**
Small online sellers in India (Instagram shops, D2C websites) get the same calls all day, in Hinglish, on noisy phone
lines: "mera parcel kahan hai?", "mila hi nahi", "return karna hai", "cancel kar do". A one- or two-person shop can't
pick up every call. Missed calls become bad reviews, and an unanswered "mila hi nahi" can turn into a chargeback weeks
later. Generic chatbots are risky here: they guess delivery dates and promise refunds the seller never agreed to.

**Who will use it:** Small online sellers and their customers. The customer calls and talks naturally in Hindi, English
or both; the seller gets every call transcribed on a dashboard and approves anything that moves money.

**Gnani AI models / APIs used:**
- Gnani **Prisma v3.0** speech-to-text, REST API (`/stt/v3`), `language_code=hi-IN,en-IN`, `format=transliterate`
  (Hinglish back in Latin letters), with `keyterms` (the shop's order numbers and products) and `topic`. Median 0.53 s per turn.
- Gnani **Timbre v3.0** text-to-speech (voice **Shivani**, `hi-en`) for every reply, and 10 other Timbre v3.0 voices
  (Riyaa, Devansh, Shubham, Kalpana, Yashraj, Avinash, Chetana, Tarika, Prakash, Lakshmi) to voice the synthetic callers
  used in the demo and the evaluation.

**Each member's contribution:** Solo entry. Aaditya Baghel: idea, product design, build (Python, Starlette, Gnani APIs,
browser audio), evaluation, demo.

## Written project explanation (paste)

Haanji answers a small online shop's customer calls in Hinglish. The caller speaks; Gnani Prisma v3.0 transcribes the
turn in about half a second, in Latin-letter Hinglish, listening for the shop's own order numbers and product names.
Haanji then works out what the caller wants (where's my parcel, it never arrived, return, cancel, damaged item, address
change, talk to a person) and answers from the shop's own order and courier records. Gnani Timbre v3.0 speaks the answer
back in a warm Hinglish voice.

Three design choices make it safe for a real shop:
1. Every sentence Haanji says is written by code from a record, and the record is shown next to it. It can't invent a
   delivery date or promise a refund.
2. No money moves on a call. Returns, cancels, refunds and complaints become tickets the seller approves with one click.
3. Caller ID decides what may be said. An unknown number gets tracking status only, and nobody can ask about someone
   else's order.

When a customer says "mila hi nahi" but the courier shows the parcel delivered with an OTP, Haanji politely shares the
proof, and if the customer still complains, the seller gets a ticket flagged as a chargeback risk, with the call
transcript and delivery proof attached.

Measured, not just demoed: 48 labelled Hinglish and English caller sentences, voiced by 10 Gnani voices, transcribed by
Gnani, then understood by Haanji. On the 28 held-out sentences (written before the first run, never tuned on): 86%
understood from text, 82% from clean audio, 68% over a simulated noisy phone line (8 kHz, mu-law, 10 dB noise). A
misunderstood turn fails safe: Haanji asks again, and after two misses offers a callback from the seller.

All data is synthetic: shop, customers, phone numbers and every voice.

Code: https://github.com/aadityabaghel25-netizen/haanji

## LinkedIn post (paste, attach the video)

> Small online sellers miss calls all day: "mera parcel kahan hai?", "mila hi nahi", "return karna hai". So I built
> **Haanji**, a Hinglish voice helpline for small sellers, on @Gnani AI's speech models.
>
> 🎙️ Gnani Prisma v3.0 hears the caller in ~0.5 s, even in Hinglish
> 📋 Code answers from the shop's own order and courier records, so it never guesses a delivery date
> 🔊 Gnani Timbre v3.0 speaks the answer back in a natural Hinglish voice
> 🎫 No money moves on a call: returns, cancels and complaints wait for the seller's click
> ⚠️ "Mila hi nahi" on a parcel the courier shows delivered gets flagged as a chargeback risk, with the proof attached
>
> I measured it too: 82% of held-out Hinglish requests understood from clean audio, 68% over a noisy 8 kHz phone line.
> Honest numbers, and the next thing to improve.
>
> Code: https://github.com/aadityabaghel25-netizen/haanji
>
> #GnaniAI #GreatIndianAIInternshipChallenge #VoiceAI #Hinglish #BuildInPublic

Tag Gnani AI's company page in the post (type @Gnani and pick the page).

## X post (paste, attach the video)

> Built Haanji: a Hinglish voice helpline for small online sellers, on @GnaniAI Prisma v3.0 + Timbre v3.0.
> "Mera parcel kahan hai?" → answered from the shop's records in seconds. No money moves without the seller's click.
> 82% held-out accuracy on clean audio, 68% on a noisy phone line.
> github.com/aadityabaghel25-netizen/haanji
> #GnaniAI #GreatIndianAIInternshipChallenge

(Check Gnani's X handle before posting.)
