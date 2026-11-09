# Haanji evaluation

Run 2026-11-09 10:16 UTC · STT `prisma-v3.0` (`hi-IN,en-IN`, transliterate) · voices: Gnani `timbre-v3.0` (10 voices, `hi-en`) · phone line: 8 kHz, 300-3400 Hz, mu-law, 10 dB SNR

A turn is right when the intent is right and any order number the caller said was picked up. The held-out set was written before the first run and is never tuned on. Both sets were written by us, and voiced by text-to-speech, so they are cleaner than real customers on real phones.

| Set | Utterances | Text only (rules) | Gnani STT, clean audio | Gnani STT, noisy phone line |
|---|---|---|---|---|
| tune | 20 | 20/20 (100%) | 20/20 (100%) | 19/20 (95%) |
| holdout | 28 | 24/28 (86%) | 23/28 (82%) | 19/28 (68%) |

Gnani STT time per turn: median **0.53 s**, slowest 0.74 s (96 requests).

## Held-out misses

| Said | Want | Text | Heard (clean) | Heard (phone) |
|---|---|---|---|---|
| Bhaiya mera order abhi kidhar hai? | status | ✓ | ✓ · Bhaiya, mera order abhi kidhar hai? | ✗ unknown · ya mera order abhi kinhar hai? |
| Mere order ka kya update hai? | status | ✗ unknown | ✗ unknown · mere order ka kya update hai? | ✗ unknown · Mere order ka kya update hai? |
| Courier wala bol raha hai de diya, par maine kuch nahi liya. | not_received | ✗ no | ✗ no · courier wala bol raha hai de diya, par maine kuch nahi liya. | ✗ no · courier wala bol raha hai, "de diya," par maine kuch nahi liya. |
| Saree ka pallu fata hua hai. | damaged | ✓ | ✓ · sari ka pallu fata hua hai. | ✗ unknown · Sari ka pallu pata hua hai. |
| Packet khola toh andar kuch aur hi tha. | damaged | ✗ unknown | ✗ unknown · packet khola toh andar kuch aur hi tha. | ✗ unknown · packet khola toh andar kuch aur hi tha. |
| Dupatta wala order radd kar dijiye. | cancel | ✓ | ✗ yes · duppatta wala order add kar dijiye. | ✗ yes · patta wala order land kar dijiye. |
| Cancel karna hai order chaar aath do chaar. | cancel 4824 | ✓ | ✓ · cancel karna hai order char aath do char. | ✗ cancel · cancel karna hai order icarat dosar. |
| Delivery ka pata badalna hai, naya address dena hai. | address | ✗ return | ✗ return · delivery ka pata badalna hai, naya address dena hai. | ✗ return · ka pata badalna hai, naya address dena hai. |
| Bas itna hi poochna tha, shukriya. | bye | ✓ | ✓ · Bas itna hi poochhna tha. Shukriya. | ✗ unknown · na hi poochhna tha. |
