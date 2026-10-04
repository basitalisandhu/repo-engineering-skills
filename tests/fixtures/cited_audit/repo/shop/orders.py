import os

DB_URL = os.environ.get("SHOP_DB_URL", "sqlite:///shop.db")


def order_total(items):
    return sum(i["price"] * i["qty"] for i in items)


def apply_discount(total, code):
    if code == "TEN":
        return total * 0.9
    return total


def legacy_export(orders):
    # Not called anywhere.
    return [o["id"] for o in orders]
