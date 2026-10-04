import json

from app.billing.invoice import Invoice
from app.core.utils import paginate
from app.reports import summary
from app.reports.formatting import fmt
from app.users.account import Account


def list_invoices(account: Account, invoices: list[Invoice]):
    return json.dumps([fmt(i.total) for i in paginate(invoices)] + [summary.build([])["total"]])
