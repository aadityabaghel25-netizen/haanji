"""
Glue: one call = a sequence of turns. Each turn is

    caller audio -> Gnani STT (Prisma v3.0, Hinglish in Latin letters) -> brain.respond (code) -> Gnani TTS (Timbre) -> audio back

Calls, turns and tickets live in SQLite so the seller's dashboard can show them.
Without a Gnani key the same flow runs on typed text (offline demo mode).
"""

import hashlib
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone

from . import brain
from .config import PROJECT_ROOT, Settings
from .gnani import GnaniError, stt, tts
from .shop import Shop

SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, phone TEXT, customer TEXT, started TEXT, ended TEXT, state TEXT);
CREATE TABLE IF NOT EXISTS turns (id INTEGER PRIMARY KEY, call_id INTEGER, who TEXT, text TEXT, intent TEXT, order_id TEXT,
    facts TEXT, stt_s REAL, tts_s REAL, audio_key TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY, call_id INTEGER, order_id TEXT, kind TEXT, summary TEXT, risk TEXT,
    status TEXT, created TEXT, decided TEXT);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Service:
    def __init__(self, settings: Settings, shop: Shop | None = None):
        self.s = settings
        self.shop = shop or Shop(settings.shop_path)
        self.cache_dir = os.path.join(PROJECT_ROOT, "data", "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.db = sqlite3.connect(settings.database_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.lock = threading.Lock()

    # ------------------------------------------------------------ voice
    def speak(self, text: str, voice: str | None = None) -> tuple[str | None, float]:
        """Gnani TTS, cached by text+voice so a repeated line costs nothing. Returns (audio key, seconds)."""
        if not self.s.voice_on:
            return None, 0.0
        voice = voice or self.s.agent_voice
        key = hashlib.sha256(f"{self.s.tts_model}|{voice}|{self.s.tts_language}|{text}".encode()).hexdigest()[:24]
        path = os.path.join(self.cache_dir, f"{key}.mp3")
        if os.path.exists(path):
            return key, 0.0
        start = time.time()
        audio = tts(self.s.gnani_api_key, text, voice=voice, model=self.s.tts_model, language=self.s.tts_language)
        with open(path, "wb") as f:
            f.write(audio)
        return key, round(time.time() - start, 2)

    def audio_path(self, key: str) -> str | None:
        path = os.path.join(self.cache_dir, f"{key}.mp3")
        return path if key.isalnum() and os.path.exists(path) else None

    def hear(self, audio: bytes, filename: str) -> tuple[str, float]:
        r = stt(self.s.gnani_api_key, audio, filename, language=self.s.stt_language, keyterms=self.shop.keyterms(),
                topic=f"Customer calling {self.shop.name}, an online clothing shop, about an order", model=self.s.stt_model)
        return r["text"], r["latency_s"]

    # ------------------------------------------------------------ calls
    def start_call(self, phone: str) -> dict:
        caller = self.shop.customer_by_phone(phone)
        with self.lock:
            cur = self.db.execute("INSERT INTO calls (phone, customer, started, state) VALUES (?,?,?,?)",
                                  (phone, caller["id"] if caller else None, now(), "{}"))
            call_id = cur.lastrowid
            self.db.commit()
        text = brain.greeting(self.shop, caller)
        key, tts_s = self.speak(text)
        self._add_turn(call_id, "agent", text, "greeting", None, [], None, tts_s, key)
        return {"call_id": call_id, "caller": caller["name"] if caller else None, "reply": text, "audio": key, "tts_s": tts_s}

    def turn(self, call_id: int, audio: bytes | None = None, filename: str = "turn.wav", text: str | None = None) -> dict:
        call = self.db.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
        if not call or call["ended"]:
            raise ValueError("This call has ended.")
        stt_s = None
        if audio:
            if not self.s.voice_on:
                raise ValueError("Voice needs a Gnani key. Type instead.")
            heard, stt_s = self.hear(audio, filename)
        else:
            heard = (text or "").strip()
        if not heard:
            reply = brain.Reply("Maaf kijiye, aapki awaaz nahi aayi. Kya aap dobara bol sakte hain?", "silence")
            state = json.loads(call["state"])
        else:
            caller = self.shop.customers.get(call["customer"]) if call["customer"] else None
            state = json.loads(call["state"])
            reply = brain.respond(heard, state, self.shop, caller)
        self._add_turn(call_id, "caller", heard, reply.intent, reply.order_id, [], stt_s, None, None)
        key, tts_s = self.speak(reply.text)
        self._add_turn(call_id, "agent", reply.text, reply.intent, reply.order_id, reply.facts, None, tts_s, key)
        ticket_id = None
        with self.lock:
            if reply.ticket:
                t = reply.ticket
                ticket_id = self.db.execute("INSERT INTO tickets (call_id, order_id, kind, summary, risk, status, created) VALUES (?,?,?,?,?,?,?)",
                                            (call_id, t.order_id, t.kind, t.summary, t.risk, "waiting", now())).lastrowid
            self.db.execute("UPDATE calls SET state=?, ended=? WHERE id=?", (json.dumps(state), now() if reply.end else None, call_id))
            self.db.commit()
        return {"heard": heard, "stt_s": stt_s, "reply": reply.text, "audio": key, "tts_s": tts_s, "intent": reply.intent,
                "order_id": reply.order_id, "facts": reply.facts, "ended": reply.end, "order": self.order_card(reply.order_id),
                "ticket": {"id": ticket_id, "summary": reply.ticket.summary, "risk": reply.ticket.risk} if reply.ticket else None}

    def order_card(self, order_id: str | None) -> dict | None:
        """The record the answer came from, for the 'order on file' card (no customer name, phone or address)."""
        o = self.shop.orders.get(order_id) if order_id else None
        if not o:
            return None
        keys = ("id", "item", "amount", "status", "courier", "awb", "shipped_on", "expected_on", "delivered_on", "proof", "last_scan")
        return {k: o.get(k) for k in keys}

    def end_call(self, call_id: int) -> None:
        with self.lock:
            self.db.execute("UPDATE calls SET ended=COALESCE(ended, ?) WHERE id=?", (now(), call_id))
            self.db.commit()

    def _add_turn(self, call_id, who, text, intent, order_id, facts, stt_s, tts_s, key) -> None:
        with self.lock:
            self.db.execute("INSERT INTO turns (call_id, who, text, intent, order_id, facts, stt_s, tts_s, audio_key, at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (call_id, who, text, intent, order_id, json.dumps(facts, ensure_ascii=False), stt_s, tts_s, key, now()))
            self.db.commit()

    # ------------------------------------------------------------ seller side
    def decide(self, ticket_id: int, approve: bool) -> None:
        """Only the seller, with a click, moves a ticket on. Nothing on a call can."""
        with self.lock:
            self.db.execute("UPDATE tickets SET status=?, decided=? WHERE id=? AND status='waiting'",
                            ("approved" if approve else "declined", now(), ticket_id))
            self.db.commit()

    def dashboard(self) -> dict:
        calls = [dict(c) for c in self.db.execute("SELECT * FROM calls ORDER BY id DESC LIMIT 30")]
        for c in calls:
            c["turns"] = [dict(t) for t in self.db.execute("SELECT * FROM turns WHERE call_id=? ORDER BY id", (c["id"],))]
            cust = self.shop.customers.get(c["customer"]) if c["customer"] else None
            c["who"] = cust["full_name"] if cust else "Unknown number"
        tickets = [dict(t) for t in self.db.execute("SELECT * FROM tickets ORDER BY (status='waiting') DESC, id DESC")]
        stt = [r[0] for r in self.db.execute("SELECT stt_s FROM turns WHERE stt_s IS NOT NULL")]
        tts_ = [r[0] for r in self.db.execute("SELECT tts_s FROM turns WHERE tts_s > 0")]
        med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
        return {"calls": calls, "tickets": tickets,
                "stats": {"calls": len(calls), "waiting": sum(t["status"] == "waiting" for t in tickets),
                          "risk": sum(bool(t["risk"]) for t in tickets), "stt_median": med(stt), "tts_median": med(tts_)}}

    KIND_SPOKEN = {"return": "return", "cancel": "cancel", "not_received": "parcel nahi mila", "damaged": "kharab ya galat item",
                   "address": "address badalna", "callback": "callback"}

    def summary_text(self) -> str:
        """The seller's spoken briefing, written by code from the call log (never by a model)."""
        d = self.dashboard()
        calls = d["stats"]["calls"]
        if not calls:
            return "Abhi tak koi call nahi aayi. Haanji line pe hai, aur har call yahan dikhegi."
        waiting = [t for t in d["tickets"] if t["status"] == "waiting"]
        parts = [f"Aaj {calls} {'call' if calls == 1 else 'calls'} aayi."]
        if waiting:
            kinds = {}
            for t in waiting:
                kinds[t["kind"]] = kinds.get(t["kind"], 0) + 1
            listed = ", ".join(f"{n} {self.KIND_SPOKEN.get(k, k)}" for k, n in kinds.items())
            parts.append(f"Approval ke liye {'request' if len(waiting) == 1 else 'requests'}: {listed}.")
        else:
            parts.append("Koi request aapka intezaar nahi kar rahi.")
        for t in waiting:
            if t["risk"] and t["order_id"]:
                o = self.shop.orders[t["order_id"]]
                parts.append(f"Dhyaan dijiye, {o.get('short') or o['item']} wale order pe chargeback ka khatra hai. Courier ke paas OTP proof hai.")
        return " ".join(parts)

    def reset(self) -> None:
        with self.lock:
            self.db.executescript("DELETE FROM calls; DELETE FROM turns; DELETE FROM tickets;")
            self.db.commit()
