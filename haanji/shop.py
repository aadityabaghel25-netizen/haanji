"""The shop's own records: customers and orders. The helpline only ever answers from these."""

import json
import re
from datetime import date, timedelta

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def resolve(value, today: date):
    """"{today-3}" -> the ISO date 3 days ago, so the demo never goes stale."""
    if isinstance(value, str):
        m = re.fullmatch(r"\{today([+-]\d+)?\}", value)
        if m:
            return (today + timedelta(days=int(m.group(1) or 0))).isoformat()
    return value


class Shop:
    def __init__(self, path: str, today: date | None = None):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self.today = today or date.today()
        self.name = raw["shop_name"]
        self.city = raw["city"]
        self.return_days = raw["return_days"]
        self.support_hours = raw["support_hours"]
        self.customers = {c["id"]: c for c in raw["customers"]}
        self.orders = {o["id"]: {k: resolve(v, self.today) for k, v in o.items()} for o in raw["orders"]}

    def customer_by_phone(self, phone: str | None) -> dict | None:
        digits = re.sub(r"\D", "", phone or "")
        for c in self.customers.values():
            if digits and re.sub(r"\D", "", c["phone"]).endswith(digits[-10:]):
                return c
        return None

    def orders_for(self, customer_id: str) -> list[dict]:
        """Newest first."""
        return sorted((o for o in self.orders.values() if o["customer"] == customer_id), key=lambda o: o["paid_on"], reverse=True)

    def keyterms(self) -> list[str]:
        """Words for Gnani to listen for: order numbers, product names, the shop's name."""
        terms = [self.name, "Haanji", "return", "refund", "cancel", "courier", "parcel"]
        for o in self.orders.values():
            terms += [o["id"], o["item"], *o["keywords"]]
        return list(dict.fromkeys(terms))


def say_date(iso: str | None, today: date) -> str:
    """"2026-11-12" -> "12 November", or "aaj" / "kal" / "parson" when close."""
    if not iso:
        return ""
    d = date.fromisoformat(iso)
    delta = (d - today).days
    near = {0: "aaj", 1: "kal", -1: "kal", 2: "parson", -2: "parson"}
    if delta in near:
        return near[delta]
    return f"{d.day} {MONTHS[d.month - 1]}"


def say_digits(number: str) -> str:
    """Order numbers are read digit by digit, the way people say them on the phone: "4 8 2 1"."""
    return " ".join(number)
