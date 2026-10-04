from app.core.utils import money
from app.users.account import Account


class Invoice:
    def __init__(self, account: Account, cents: int):
        self.account = account
        self.total = money(cents)
