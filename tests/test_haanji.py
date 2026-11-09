"""Offline tests: no Gnani calls. Run: python3 -m unittest discover -s tests -v"""

import os
import sys
import tempfile
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from haanji.audio import fix_wav_header, phone_line  # noqa: E402
from haanji.brain import digits_in, greeting, respond, understand  # noqa: E402
from haanji.config import Settings  # noqa: E402
from haanji.service import Service  # noqa: E402
from haanji.shop import Shop, say_date, say_digits  # noqa: E402
from evals.utterances import TUNE  # noqa: E402

TODAY = date(2026, 11, 9)
SHOP_PATH = os.path.join(ROOT, "data", "shop.json")


def shop():
    return Shop(SHOP_PATH, today=TODAY)


def talk(sh, phone, lines):
    caller, state, out = sh.customer_by_phone(phone), {}, []
    for line in lines:
        out.append(respond(line, state, sh, caller))
    return out


class NumberTests(unittest.TestCase):
    def test_spoken_digits(self):
        self.assertEqual(digits_in("order four eight two one"), ["4821"])
        self.assertEqual(digits_in("order chaar aath do ek"), ["4821"])
        self.assertEqual(digits_in("forty eight twenty three"), ["4823"])
        self.assertEqual(digits_in("4824 cancel"), ["4824"])

    def test_hindi_verb_do_is_not_two(self):
        self.assertEqual(digits_in("cancel kar do"), [])
        self.assertEqual(digits_in("no thanks"), [])

    def test_dates_and_digits_are_said_naturally(self):
        self.assertEqual(say_date("2026-11-10", TODAY), "kal")
        self.assertEqual(say_date("2026-11-20", TODAY), "20 November")
        self.assertEqual(say_digits("4821"), "4 8 2 1")


class UnderstandTests(unittest.TestCase):
    def test_tune_set_understood_from_text(self):
        sh = shop()
        for text, intent, order in TUNE:
            u = understand(text, sh)
            self.assertEqual(u.intent, intent, text)
            if order:
                self.assertIn(order, u.order_ids, text)

    def test_product_names_point_to_orders(self):
        self.assertEqual(understand("bedsheet ka kya hua", shop()).product_orders, ["4822"])


class ConversationTests(unittest.TestCase):
    def test_greets_known_caller_by_name_and_says_it_is_ai(self):
        sh = shop()
        g = greeting(sh, sh.customer_by_phone("+91 90000 00001"))
        self.assertIn("Priya ji", g)
        self.assertIn("AI assistant", g)

    def test_status_comes_from_the_record(self):
        r = talk(shop(), "+91 90000 00001", ["mera kurti kab tak aayega"])[0]
        self.assertEqual((r.intent, r.order_id), ("status", "4821"))
        self.assertIn("Delhivery", r.text)
        self.assertIn("parson", r.text.lower())   # expected two days from today in the demo data

    def test_not_received_cites_proof_and_flags_chargeback_risk(self):
        first, ticket = talk(shop(), "+91 90000 00002", ["mera bedsheet nahi mila", "haan darj kar dijiye"])
        self.assertIn("OTP", first.text)
        self.assertIsNone(first.ticket)                       # nothing happens without a yes
        self.assertEqual(ticket.ticket.kind, "not_received")
        self.assertIn("Chargeback risk", ticket.ticket.risk)

    def test_saying_no_creates_nothing(self):
        _, r = talk(shop(), "+91 90000 00003", ["mujhe return karna hai", "nahi rehne do"])
        self.assertIsNone(r.ticket)

    def test_return_window_enforced_by_code(self):
        sh = shop()
        ok = talk(sh, "+91 90000 00003", ["saree return karna hai"])[0]     # delivered 3 days ago
        self.assertIn("return ho sakta hai", ok.text)
        late = talk(sh, "+91 90000 00001", ["cushion cover return karna hai"])[0]   # delivered 15 days ago
        self.assertIn("khatam ho gaya", late.text)

    def test_cancel_only_before_shipping(self):
        sh = shop()
        packed = talk(sh, "+91 90000 00004", ["order cancel karna hai", "haan"])
        self.assertEqual(packed[1].ticket.kind, "cancel")
        shipped = talk(sh, "+91 90000 00001", ["kurti cancel karni hai"])[0]
        self.assertIn("ab cancel nahi ho sakta", shipped.text)

    def test_refund_amount_is_the_order_amount(self):
        r = talk(shop(), "+91 90000 00003", ["saree return karna hai"])[0]
        self.assertIn("₹3499", r.text)

    def test_unknown_caller_gets_tracking_only(self):
        sh = shop()
        r = talk(sh, "+91 98765 00000", ["mera order kahan hai", "order number chaar aath do teen", "return karna hai"])
        self.assertIn("order number", r[0].text)
        self.assertNotIn("Sameer", r[1].text)                 # no name of who received it
        self.assertIn("registered phone number", r[2].text)
        self.assertIsNone(r[2].ticket)

    def test_caller_cannot_ask_about_someone_elses_order(self):
        r = talk(shop(), "+91 90000 00001", ["order four eight two two ka status"])[0]
        self.assertEqual(r.intent, "unknown_order")
        self.assertNotIn("bedsheet", r.text)

    def test_asks_which_order_when_caller_has_two(self):
        r = talk(shop(), "+91 90000 00001", ["return karna hai", "cushion cover wala"])
        self.assertIn("2 orders", r[0].text)
        self.assertEqual(r[1].order_id, "4825")

    def test_two_misses_offer_a_human(self):
        r = talk(shop(), "+91 90000 00002", ["blah blah", "hmm kuch nahi"])
        self.assertIn("call back", r[1].text)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Settings(gnani_api_key="", stt_model="prisma-v3.0", stt_language="hi-IN,en-IN", tts_model="timbre-v3.0",
                          agent_voice="Shivani", tts_language="hi-en", shop_path=SHOP_PATH,
                          database_path=os.path.join(self.tmp.name, "t.db"), seller_password="")
        self.svc = Service(self.s, Shop(SHOP_PATH, today=TODAY))

    def tearDown(self):
        self.svc.db.close()
        self.tmp.cleanup()

    def test_offline_typed_call_and_seller_approval(self):
        c = self.svc.start_call("+91 90000 00002")
        self.assertIsNone(c["audio"])                         # no key: no voice, still works
        self.svc.turn(c["call_id"], text="bedsheet nahi mila")
        r = self.svc.turn(c["call_id"], text="haan")
        self.assertTrue(r["ticket"]["risk"])
        d = self.svc.dashboard()
        self.assertEqual(d["stats"]["waiting"], 1)
        self.svc.decide(r["ticket"]["id"], approve=True)
        self.assertEqual(self.svc.dashboard()["tickets"][0]["status"], "approved")

    def test_spoken_summary_is_written_from_the_log(self):
        self.assertIn("koi call nahi", self.svc.summary_text())
        c = self.svc.start_call("+91 90000 00002")
        self.svc.turn(c["call_id"], text="bedsheet nahi mila")
        self.svc.turn(c["call_id"], text="haan")
        text = self.svc.summary_text()
        self.assertIn("Aaj 1 call aayi", text)
        self.assertIn("1 parcel nahi mila", text)
        self.assertIn("chargeback ka khatra", text)

    def test_voice_needs_a_key(self):
        c = self.svc.start_call("+91 90000 00001")
        with self.assertRaises(ValueError):
            self.svc.turn(c["call_id"], audio=b"RIFF....")

    def test_ended_call_takes_no_more_turns(self):
        c = self.svc.start_call("+91 90000 00001")
        self.assertTrue(self.svc.turn(c["call_id"], text="theek hai bye")["ended"])
        with self.assertRaises(ValueError):
            self.svc.turn(c["call_id"], text="hello")


class AudioTests(unittest.TestCase):
    def test_phone_line_makes_8k_audio(self):
        import io
        import math
        import struct
        import wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
            w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * n / 16000))) for n in range(16000)))
        out = phone_line(buf.getvalue(), 10)
        with wave.open(io.BytesIO(out)) as r:
            self.assertEqual((r.getframerate(), r.getnframes()), (8000, 8000))

    def test_fix_wav_header(self):
        broken = b"RIFF\xff\xff\xff\xffWAVEfmt \x10\x00\x00\x00" + b"\x00" * 16 + b"data\xff\xff\xff\xff" + b"\x01\x02" * 10
        fixed = fix_wav_header(broken)
        self.assertEqual(int.from_bytes(fixed[fixed.find(b"data") + 4:][:4], "little"), 20)


if __name__ == "__main__":
    unittest.main()
