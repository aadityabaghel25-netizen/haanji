"""
The helpline's brain, in plain code. No language model: it can't invent a delivery date or promise a refund.

understand(text)  -> what the caller wants (intent) and any order number or product they named.
respond(...)      -> the next thing to say, written from the shop's records, plus any ticket for the seller.

Money never moves on a call. Returns, refunds, cancellations and complaints become tickets that the seller
approves with a click on the dashboard.
"""

import re
from dataclasses import dataclass, field
from datetime import date

from .shop import Shop, say_date, say_digits

# ---------------------------------------------------------------- numbers spoken as words
UNITS = {"zero": 0, "shunya": 0, "oh": 0, "one": 1, "ek": 1, "two": 2, "do": 2, "three": 3, "teen": 3, "four": 4, "char": 4,
         "chaar": 4, "five": 5, "paanch": 5, "panch": 5, "six": 6, "chhe": 6, "chhah": 6, "che": 6, "seven": 7, "saat": 7,
         "sat": 7, "eight": 8, "aath": 8, "ath": 8, "nine": 9, "nau": 9, "no": None}
TEENS = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
         "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
# "do" (two) is also the Hindi verb "do" ("cancel kar do"), and "no" is English. Only count them inside a run of numbers.
AMBIGUOUS = {"do", "no", "oh", "sat", "che", "ath"}


def digits_in(text: str) -> list[str]:
    """Every run of numbers in the text, spoken or written: "order four eight two one" -> ["4821"],
    "forty eight twenty one" -> ["4821"], "4821" -> ["4821"]."""
    tokens = re.findall(r"[a-z]+|\d+", text.lower().replace("-", " "))
    runs, cur = [], []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        piece = None
        if t.isdigit():
            piece = t
        elif t in TENS:
            value = TENS[t]
            if i + 1 < len(tokens) and UNITS.get(tokens[i + 1]) not in (None, 0):
                value += UNITS[tokens[i + 1]]
                i += 1
            piece = str(value)
        elif t in TEENS:
            piece = str(TEENS[t])
        elif t in UNITS and UNITS[t] is not None:
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            in_run = bool(cur) or nxt.isdigit() or (nxt in UNITS and UNITS[nxt] is not None) or nxt in TENS or nxt in TEENS
            if t not in AMBIGUOUS or in_run:
                piece = str(UNITS[t])
        if piece is not None:
            cur.append(piece)
        elif cur:
            runs.append("".join(cur))
            cur = []
        i += 1
    if cur:
        runs.append("".join(cur))
    return runs


# ---------------------------------------------------------------- what the caller wants
# Checked in this order; the first match wins. Hinglish has no fixed spelling, so each idea has several spellings.
INTENTS = [
    ("human", r"\b(insaan|insan|human|real person|seller se|owner se|manager|aadmi se|kisi se baat|baat karwa|baat karni|call back|callback)\b"),
    ("cancel", r"\b(cancel|cancle|radd|nahi chahiye ab)\b"),
    ("not_received", r"\b(nahi mila|nahin mila|nai mila|mila hi nahi|nahi aaya|nahin aaya|nai aaya|aaya hi nahi|receive nahi|deliver nahi|not received|didn'?t (get|receive)|never (got|received|came))\b"),
    ("return", r"\b(return|wapas|vapas|refund|paise|paisa|exchange|badal\w*)\b"),
    ("damaged", r"\b(toot|tuta|tooti|tuti|toota|phata|phati|fata|fati|damage\w*|kharab|ganda|daag|defect\w*|broken|torn|galat|wrong|alag|different|size chhota|size bada|fit nahi)\b"),
    ("address", r"\b(address|pata badal|pata change|location)\b"),
    ("status", r"\b(kahan|kaha|kidhar|status|track\w*|kab tak|kab aay\w*|kab milega|kab ayega|kab aaega|deliver\w*|pahunch\w*|where|when|kab)\b"),
    ("bye", r"\b(bas itna|bas|bye|dhanyavaad|dhanyawad|dhanyavad|thank\w*|shukriya|theek hai bas|ok bye|rakhti|rakhta)\b"),
    ("yes", r"\b(haan|haa|han|ha ji|haan ji|ji haan|yes|yeah|ok|okay|theek|thik|sahi|zaroor|bilkul|kar do|kar dijiye|kijiye)\b"),
    ("no", r"\b(nahi|nahin|nai|no|mat|rehne do|rahne do)\b"),
]


@dataclass
class Understanding:
    intent: str
    order_ids: list[str] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)
    product_orders: list[str] = field(default_factory=list)


def understand(text: str, shop: Shop) -> Understanding:
    t = " " + re.sub(r"[^\w' ]+", " ", text.lower()) + " "
    intent = next((name for name, pattern in INTENTS if re.search(pattern, t)), "unknown")
    numbers = digits_in(t)
    order_ids = [n for n in numbers if n in shop.orders]
    product_orders = [o["id"] for o in shop.orders.values() if any(re.search(rf"\b{re.escape(k)}", t) for k in o["keywords"])]
    return Understanding(intent, order_ids, numbers, product_orders)


# ---------------------------------------------------------------- what to say next
@dataclass
class Ticket:
    kind: str          # return, cancel, not_received, damaged, address, callback
    order_id: str | None
    summary: str
    risk: str = ""     # e.g. "chargeback risk: delivery proof on file"


@dataclass
class Reply:
    text: str
    intent: str
    order_id: str | None = None
    facts: list[str] = field(default_factory=list)    # the records this answer came from, shown to the seller
    ticket: Ticket | None = None
    end: bool = False


def greeting(shop: Shop, caller: dict | None) -> str:
    who = f"Namaste {caller['name']} ji! " if caller else "Namaste! "
    return f"{who}{shop.name} helpline. Main shop ki AI assistant hoon. Bataiye, kya madad karoon?"


def respond(text: str, state: dict, shop: Shop, caller: dict | None) -> Reply:
    """One turn of the call. `state` is the call's memory between turns: the order being discussed,
    what we're waiting for (an order number, a yes/no), and how many times we didn't understand."""
    u = understand(text, shop)
    pending = state.get("pending")

    # 1. Order the caller means: named number, named product, the one we were already on, or their only order.
    mine = [o["id"] for o in shop.orders_for(caller["id"])] if caller else []
    order_id = None
    for oid in u.order_ids:
        if not caller or oid in mine:
            order_id = oid
            break
    if order_id is None and u.order_ids and caller:
        # Someone asking about another customer's order: don't confirm it exists.
        return Reply("Yeh order number aapke phone number se juda nahi hai. Kripya apne order ka number dobara bataiye.", "unknown_order")
    if order_id is None and u.numbers and not u.order_ids and pending in ("order_number", None) and not caller:
        return Reply(f"Order number {say_digits(u.numbers[0])} mujhe nahi mila. Kripya order confirmation SMS mein likha chaar ank ka number bataiye.",
                     "unknown_order")
    if order_id is None and u.product_orders:
        options = [o for o in u.product_orders if not caller or o in mine]
        if len(options) == 1:
            order_id = options[0]
    if order_id is None:
        order_id = state.get("order_id")
    if order_id is None and len(mine) == 1:
        order_id = mine[0]

    # 2. Waiting for a yes/no on a ticket we offered.
    if pending and pending.startswith("confirm:") and u.intent in ("yes", "no"):
        kind = pending.split(":", 1)[1]
        state["pending"] = None
        if u.intent == "no":
            return Reply("Theek hai, maine kuch darj nahi kiya. Aur kuch madad chahiye?", "no", state.get("order_id"))
        return _make_ticket(kind, state.get("order_id"), shop, state)

    intent = u.intent
    if intent in ("yes", "no", "unknown") and pending == "intent_after_order" and order_id:
        intent = state.get("wanted", "status")
    if intent in ("unknown", "yes", "no") and pending == "order_number" and order_id:
        intent = state.get("wanted", "status")

    if intent == "bye":
        state["pending"] = None
        return Reply("Dhanyavaad! Aapka din shubh ho.", "bye", order_id, end=True)
    if intent == "human":
        return _offer("callback", order_id, shop, state,
                      f"Main seller ko aapko call back karne ke liye bol sakti hoon, {shop.support_hours}. Kya main callback request darj karoon?")
    if intent in ("unknown", "yes", "no"):
        state["misses"] = state.get("misses", 0) + 1
        if state["misses"] >= 2:
            return _offer("callback", order_id, shop, state,
                          "Maaf kijiye, mujhe theek se samajh nahi aaya. Kya main seller se aapko call back karwa doon?")
        return Reply("Maaf kijiye, main samajh nahi paayi. Aap order ka status, return, cancel ya koi complaint ke baare mein pooch sakte hain.",
                     "unknown", order_id)

    # 3. Everything below needs to know the order.
    if order_id is None:
        state.update(pending="order_number", wanted=intent)
        if caller and len(mine) > 1:
            names = " ya ".join(shop.orders[o]["item"] for o in mine[:3])
            return Reply(f"Aapke {len(mine)} orders hain: {names}. Kaunse order ke baare mein baat kar rahe hain?", intent)
        return Reply("Zaroor. Kripya apna chaar ank ka order number bataiye. Yeh order confirmation SMS mein likha hai.", intent)
    state["order_id"] = order_id
    state["pending"] = None
    order = shop.orders[order_id]
    if caller is None and intent not in ("status", "not_received"):
        # Unknown number: tracking only. Anything that changes an order needs the phone number on the order.
        return Reply(f"Order {say_digits(order_id)} ke liye yeh request sirf order wale registered phone number se ho sakti hai. "
                     "Kripya usi number se call kijiye.", intent, order_id, facts=[f"Order {order_id}: caller's number isn't on it"])
    return _answer(intent, order, shop, state, known_caller=caller is not None)


def _answer(intent: str, o: dict, shop: Shop, state: dict, known_caller: bool) -> Reply:
    today = shop.today
    oid, item = o["id"], o["item"]
    facts = [f"Order {oid}: {item}, ₹{o['amount']}, status {o['status']}"]
    if o.get("courier"):
        facts.append(f"{o['courier']} AWB {o['awb']}")
    delivered = o["status"] == "delivered"

    if intent in ("status", "not_received") and not delivered:
        if o["status"] == "packed":
            text = (f"Aapka {item} pack ho gaya hai, jaldi ship hoga. Lagbhag {say_date(o['expected_on'], today)} tak pahunch jaayega, "
                    "aur ship hote hi SMS aayega.")
        else:
            text = (f"Aapka {item} {o['courier']} se ship ho chuka hai, abhi {o.get('last_scan', 'raaste mein')} pe hai. "
                    f"{say_date(o['expected_on'], today).capitalize()} tak pahunch jaayega.")
            facts.append(f"Shipped {o['shipped_on']}, last scan {o.get('last_scan')}, expected {o['expected_on']}")
        return Reply(text + " Aur kuch?", intent, oid, facts)

    if intent == "status":
        text = f"Aapka {item} {say_date(o['delivered_on'], today)} deliver ho chuka hai."
        if known_caller and o.get("received_by"):
            text += f" {o['received_by']} ne receive kiya tha."
        facts.append(f"Delivered {o['delivered_on']}, {o.get('proof', '')}")
        return Reply(text + " Kya parcel mil gaya?", intent, oid, facts)

    if intent == "not_received":
        facts.append(f"Delivered {o['delivered_on']} to {o.get('received_by')}, {o.get('proof')}")
        who = f", {o['received_by']} ne receive kiya" if known_caller and o.get("received_by") else ""
        text = (f"{o['courier']} ke record mein aapka {item} {say_date(o['delivered_on'], today)} OTP se deliver hua tha{who}. "
                "Ek baar ghar pe pooch lijiye. Phir bhi nahi mila, toh complaint darj karoon?")
        state["pending"] = "confirm:not_received"
        return Reply(text, intent, oid, facts)

    if intent == "damaged":
        if not delivered:
            return Reply(f"Aapka {item} abhi deliver nahi hua hai. Milne ke baad koi problem ho toh zaroor call kijiye.", intent, oid, facts)
        state["pending"] = "confirm:damaged"
        return Reply(f"Maaf kijiye, {item} mein problem aayi. Seller WhatsApp pe photo maangega. Complaint darj karoon?", intent, oid, facts)

    if intent == "return":
        if not delivered:
            return Reply(f"Aapka {item} abhi deliver nahi hua hai, isliye return abhi nahi ho sakta. Agar aapko yeh nahi chahiye, toh main cancel request darj kar sakti hoon.",
                         intent, oid, facts)
        days = (today - date.fromisoformat(o["delivered_on"])).days
        last = date.fromordinal(date.fromisoformat(o["delivered_on"]).toordinal() + shop.return_days).isoformat()
        facts.append(f"Delivered {o['delivered_on']}, {days} days ago; return window {shop.return_days} days, until {last}")
        if days > shop.return_days:
            state["pending"] = "confirm:callback"
            return Reply(f"Aapka {item} {days} din pehle deliver hua tha. Return sirf {shop.return_days} din tak hota hai, jo {say_date(last, today)} ko khatam ho gaya. "
                         "Kya main seller se aapko callback karwa doon?", intent, oid, facts)
        state["pending"] = "confirm:return"
        return Reply(f"Haan, aapka {item} {say_date(last, today)} tak return ho sakta hai. Seller approve karega, pickup hoga, "
                     f"aur ₹{o['amount']} ka refund aapke original payment mein aayega. Request darj karoon?", intent, oid, facts)

    if intent == "cancel":
        if o["status"] == "packed":
            state["pending"] = "confirm:cancel"
            return Reply(f"Aapka {item} abhi ship nahi hua, isliye cancel ho sakta hai. Seller confirm karega, aur ₹{o['amount']} ka refund "
                         "original payment mein aayega. Cancel request darj karoon?", intent, oid, facts)
        if delivered:
            return _answer("return", o, shop, state, known_caller)
        return Reply(f"Aapka {item} ship ho chuka hai, isliye ab cancel nahi ho sakta. Delivery ke baad aap {shop.return_days} din mein return kar sakte hain.",
                     intent, oid, facts)

    if intent == "address":
        if o["status"] == "packed":
            state["pending"] = "confirm:address"
            return Reply("Parcel abhi ship nahi hua, isliye address badla ja sakta hai. Main request darj kar deti hoon, seller naya address WhatsApp pe confirm karega. Darj karoon?",
                         intent, oid, facts)
        return Reply("Parcel ship ho chuka hai, isliye ab address nahi badla ja sakta. Courier ki delivery call pe aap unse baat kar sakte hain.", intent, oid, facts)

    return Reply("Maaf kijiye, main samajh nahi paayi.", "unknown", oid)


def _offer(kind: str, order_id, shop: Shop, state: dict, text: str) -> Reply:
    state["pending"] = f"confirm:{kind}"
    if order_id:
        state["order_id"] = order_id
    return Reply(text, kind if kind != "callback" else "human", order_id)


TICKET_TEXT = {
    "return": ("Return request", "Return request darj ho gayi. Seller approve karte hi pickup ka SMS aayega."),
    "cancel": ("Cancel request", "Cancel request darj ho gayi. Seller confirm karte hi refund shuru hoga."),
    "not_received": ("Says not received", "Complaint darj ho gayi. Seller courier se baat karke 24 ghante mein call karega."),
    "damaged": ("Damaged or wrong item", "Complaint darj ho gayi. Seller WhatsApp pe photo ke liye message karega."),
    "address": ("Address change", "Request darj ho gayi hai. Seller WhatsApp pe naya address confirm karega."),
    "callback": ("Callback", "Theek hai, seller aapko jald call karega."),
}


def _make_ticket(kind: str, order_id, shop: Shop, state: dict) -> Reply:
    title, said = TICKET_TEXT[kind]
    risk = ""
    if kind == "not_received" and order_id and shop.orders[order_id].get("proof"):
        o = shop.orders[order_id]
        risk = f"Chargeback risk: courier shows delivered {o['delivered_on']} ({o['proof']}). Keep this call as evidence."
    ticket = Ticket(kind, order_id, f"{title}{' for order ' + order_id if order_id else ''}", risk)
    return Reply(said + " Aur kuch?", kind, order_id, ticket=ticket)
