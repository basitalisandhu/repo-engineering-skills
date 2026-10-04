from ..core.utils import to_csv
from .summary import build


def export(totals):
    return to_csv([build(totals).values()])
