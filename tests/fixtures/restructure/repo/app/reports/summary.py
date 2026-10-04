from app.core.utils import money, now


def build(totals):
    return {"at": now().isoformat(), "total": money(sum(totals))}
