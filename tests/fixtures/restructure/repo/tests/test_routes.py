from app.api.routes import list_invoices
from app.core.utils import paginate


def test_paginate():
    assert paginate([1, 2, 3], 2) == [[1, 2], [3]]
    assert list_invoices
