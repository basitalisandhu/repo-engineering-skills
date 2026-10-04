"""Shared helpers that every package reaches for."""
import datetime
import re


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def money(cents):
    return f"{cents / 100:.2f}"


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def paginate(items, size=20):
    return [items[i:i + size] for i in range(0, len(items), size)]


def to_csv(rows):
    return "\n".join(",".join(map(str, r)) for r in rows)
