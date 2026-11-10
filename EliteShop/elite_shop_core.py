"""ELITE Shop domain logic and JSON persistence."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ShopError(Exception):
    """Expected business-rule error shown to a shopper."""


@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    category: str
    price: int
    description: str
    eligible_for_discount: bool = True


def _products() -> dict[str, Product]:
    groups = {
        "lifestyle": ("ELITE Lifestyle", [("Premium Newspaper", 35), ("Parker Luxury Pen", 450), ("Travel Bag", 4500), ("Luxury Comb", 250), ("Fragrance Soap", 180)]),
        "gourmet": ("ELITE Gourmet", [("Almond Milk", 180), ("Sourdough Bread", 250), ("Farm Eggs", 120), ("Greek Yogurt", 180), ("Korean Noodles", 180)]),
        "smart": ("ELITE Smart Living", [("Smart LED Bulb", 450), ("Smart Switch", 850), ("Modular Plug", 250), ("Night Lamp", 1500), ("Extension Board", 1800)]),
        "fashion": ("ELITE Fashion", [("Premium Watch", 8500), ("Designer Sunglasses", 4200), ("Leather Wallet", 2800), ("Luxury Handbag", 12500), ("Premium Footwear", 6500)]),
        "electronics": ("ELITE Electronics", [("Wireless Headphones", 5999), ("Smartwatch", 7499), ("Mechanical Keyboard", 4999), ("Premium Speakers", 8999), ("Wireless Earbuds", 3499)]),
        "beauty": ("ELITE Beauty & Care", [("Premium Perfume", 5500), ("Skincare Collection", 3200), ("Grooming Kit", 2400), ("Hair-care Set", 1800), ("Body-care Collection", 2100)]),
        "workspace": ("ELITE Workspace", [("Executive Notebook", 850), ("Fountain Pen", 2200), ("Desk Organiser", 1600), ("Office Chair", 18500), ("Laptop Stand", 3200)]),
        "home": ("ELITE Home & Living", [("Designer Lamp", 4500), ("Premium Wall Clock", 3800), ("Luxury Bedsheet", 5200), ("Decorative Vase", 2400), ("Smart Home Hub", 6999)]),
    }
    products: dict[str, Product] = {}
    for category, (label, items) in groups.items():
        for number, (name, price) in enumerate(items, 1):
            product_id = f"{category[:3].upper()}-{number:02d}"
            products[product_id] = Product(product_id, name, label, price, f"Curated {label.lower()} selection")
    if len(products) != len(set(products)) or any(item.price <= 0 for item in products.values()):
        raise ValueError("Invalid product catalogue")
    return products


PRODUCTS = _products()
MYSTERY_BOXES = {
    "classic": {"name": "Classic", "price": 199, "classification": "Standard", "contents": ["LIF-02", "LIF-05"]},
    "premium": {"name": "Premium", "price": 499, "classification": "Select", "contents": ["FAS-02", "BEA-03"]},
    "executive": {"name": "Executive", "price": 999, "classification": "Premium", "contents": ["ELE-03", "WOR-02"]},
    "signature": {"name": "Signature", "price": 1999, "classification": "Signature", "contents": ["HOM-01", "FAS-01", "ELE-05"]},
}
TIERS = (("Diamond", 10000, 8), ("Gold", 5000, 5), ("Silver", 2000, 3), ("Bronze", 0, 0))
ACHIEVEMENTS = {
    "first_purchase": ("First Purchase", 50), "explorer": ("Explorer", 40), "collector": ("Collector", 60),
    "loyal_customer": ("Loyal Customer", 100), "mystery_collector": ("Mystery Collector", 75), "elite_legend": ("ELITE Legend", 200),
}


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()


def _new_account(username: str, password: str, balance: int) -> dict[str, Any]:
    salt = secrets.token_hex(16)
    return {"username": username, "password": _hash_password(password, salt), "salt": salt, "balance": balance,
            "inventory": {}, "transactions": [], "eligible_spending": 0, "points": 0, "lifetime_points": 0,
            "points_redeemed": 0, "achievements": [], "categories_seen": [], "boxes": [], "purchase_count": 0}


class AccountStore:
    def __init__(self, path: str | Path = "elite_accounts.json") -> None:
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        try:
            with self.path.open(encoding="utf-8") as file:
                value = json.load(file)
            return value if isinstance(value, dict) and isinstance(value.get("accounts"), dict) else {"accounts": {}}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {"accounts": {}}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=".elite-", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(self.data, file, indent=2)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def register(self, username: str, password: str, balance: int = 10000) -> dict[str, Any]:
        if not username.strip() or not password:
            raise ShopError("Username and password are required.")
        if username in self.data["accounts"]:
            raise ShopError("That account already exists.")
        account = _new_account(username, password, balance)
        self.data["accounts"][username] = account
        self.save()
        return account

    def authenticate(self, username: str, password: str) -> dict[str, Any]:
        account = self.data["accounts"].get(username)
        if not account or not secrets.compare_digest(account["password"], _hash_password(password, account["salt"])):
            raise ShopError("Invalid username or password.")
        return account


def membership(account: dict[str, Any]) -> tuple[str, int]:
    for name, threshold, discount in TIERS:
        if int(account.get("eligible_spending", 0)) >= threshold:
            return name, discount
    return "Bronze", 0


def next_tier(account: dict[str, Any]) -> tuple[str | None, int]:
    spending = int(account.get("eligible_spending", 0))
    for name, threshold, _ in reversed(TIERS[:-1]):
        if spending < threshold:
            return name, threshold - spending
    return None, 0


def _award_new_achievements(account: dict[str, Any]) -> list[tuple[str, int]]:
    old = set(account.get("achievements", []))
    unlocked = set(old)
    if account["purchase_count"] >= 1: unlocked.add("first_purchase")
    if len(account["categories_seen"]) == len({p.category for p in PRODUCTS.values()}): unlocked.add("explorer")
    if len(account["inventory"]) >= 5: unlocked.add("collector")
    if account["purchase_count"] >= 5: unlocked.add("loyal_customer")
    if len(set(account["boxes"])) >= 3: unlocked.add("mystery_collector")
    if len(unlocked) >= 5: unlocked.add("elite_legend")
    account["achievements"] = sorted(unlocked)
    earned = [(ACHIEVEMENTS[key][0], ACHIEVEMENTS[key][1]) for key in account["achievements"] if key not in old]
    award = sum(points for _, points in earned)
    account["points"] += award
    account["lifetime_points"] += award
    return earned


def purchase(account: dict[str, Any], cart: dict[str, int], redeem_points: int = 0) -> dict[str, Any]:
    if not cart or any(product_id not in PRODUCTS or quantity <= 0 for product_id, quantity in cart.items()):
        raise ShopError("Cart contains an invalid product or quantity.")
    tier, discount = membership(account)
    subtotal = sum(PRODUCTS[key].price * quantity for key, quantity in cart.items())
    eligible = sum(PRODUCTS[key].price * quantity for key, quantity in cart.items() if PRODUCTS[key].eligible_for_discount)
    discount_amount = eligible * discount // 100
    after_discount = subtotal - discount_amount
    if redeem_points < 0 or redeem_points > account["points"] or redeem_points % 100:
        raise ShopError("Reward redemption must use available points in multiples of 100.")
    credit = min(redeem_points // 100 * 10, after_discount)
    actually_redeemed = credit // 10 * 100
    total = after_discount - credit
    if account["balance"] < total:
        raise ShopError("Insufficient balance.")
    transaction_id = uuid.uuid4().hex
    account["balance"] -= total
    account["points"] -= actually_redeemed
    account["points_redeemed"] += actually_redeemed
    account["eligible_spending"] += eligible
    account["purchase_count"] += 1
    for product_id, quantity in cart.items():
        product = PRODUCTS[product_id]
        account["inventory"][product_id] = account["inventory"].get(product_id, 0) + quantity
        if product.category not in account["categories_seen"]: account["categories_seen"].append(product.category)
    purchase_points = min(100, eligible // 100)
    account["points"] += purchase_points
    account["lifetime_points"] += purchase_points
    unlocked = _award_new_achievements(account)
    account["transactions"].append({"id": transaction_id, "type": "purchase", "items": dict(cart), "total": total,
                                     "eligible": eligible, "purchase_points": purchase_points, "redeemed_points": actually_redeemed, "refunded": False})
    return {"id": transaction_id, "subtotal": subtotal, "discount": discount_amount, "total": total,
            "membership": tier, "purchase_points": purchase_points, "achievements": unlocked}


def purchase_box(account: dict[str, Any], box_key: str) -> dict[str, Any]:
    box = MYSTERY_BOXES.get(box_key)
    if not box: raise ShopError("Unknown mystery box.")
    if account["balance"] < box["price"]: raise ShopError("Insufficient balance.")
    transaction_id = uuid.uuid4().hex
    account["balance"] -= box["price"]
    account["boxes"].append(box_key)
    for product_id in box["contents"]: account["inventory"][product_id] = account["inventory"].get(product_id, 0) + 1
    account["transactions"].append({"id": transaction_id, "type": "mystery_box", "box": box_key, "total": box["price"], "refunded": False})
    unlocked = _award_new_achievements(account)
    return {"id": transaction_id, "box": box, "contents": [PRODUCTS[key].name for key in box["contents"]], "achievements": unlocked}


def refund(account: dict[str, Any], transaction_id: str) -> None:
    transaction = next((item for item in account["transactions"] if item["id"] == transaction_id), None)
    if not transaction or transaction.get("refunded") or transaction.get("type") != "purchase": raise ShopError("Refund is unavailable for that transaction.")
    account["balance"] += transaction["total"]
    account["eligible_spending"] = max(0, account["eligible_spending"] - transaction["eligible"])
    account["points"] = max(0, account["points"] - transaction["purchase_points"])
    for product_id, quantity in transaction["items"].items():
        account["inventory"][product_id] -= quantity
        if account["inventory"][product_id] <= 0: del account["inventory"][product_id]
    transaction["refunded"] = True
    account["purchase_count"] = max(0, account["purchase_count"] - 1)