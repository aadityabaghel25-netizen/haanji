# What broke while building Haanji, and what we did

1. **Gnani writes spoken numbers as English words.** "Order chaar aath do ek" came back as "order four eight two one". A
   small parser (`brain.digits_in`) turns runs of number words (English and Hindi, including "forty eight twenty one")
   into digits, and ignores the Hindi verb "do" ("cancel kar do") unless it sits inside a run of numbers.
2. **Gnani's streamed WAV has placeholder sizes in its header**, so Python's `wave` module reported 24-hour clips. Code
   rewrites the header (`audio.fix_wav_header`).
3. **Browsers record WebM, Gnani's REST API takes WAV/MP3/OGG/FLAC/AAC/M4A.** The page records raw audio at 16 kHz and
   writes a WAV file itself (`static/phone.js`).
4. **Telephone audio is worse than a laptop mic.** To measure it without real calls (Gnani asks for synthetic data only),
   a simulated phone line (8 kHz, 300-3400 Hz, mu-law, noise) runs in the evaluation and in a demo toggle. It costs about
   14 points of accuracy on held-out sentences, mostly on short words.
5. **Hinglish has no fixed spelling** ("nahi / nahin / nai", "wapas / vapas"). Gnani's `transliterate` output plus
   several spellings per keyword in the rules.
6. **Measuring honestly.** A held-out set was written before the first run and is frozen; its misses (86% / 82% / 68%)
   are reported as they are.
