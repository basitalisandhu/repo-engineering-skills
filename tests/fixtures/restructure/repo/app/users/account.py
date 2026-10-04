from app.billing.invoice import Invoice
from app.core.utils import slugify


class Account:
    def __init__(self, name):
        self.slug = slugify(name)
        self.invoices: list[Invoice] = []
