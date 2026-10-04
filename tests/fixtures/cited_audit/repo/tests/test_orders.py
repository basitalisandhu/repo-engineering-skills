from shop.orders import order_total


def test_total():
    assert order_total([{"price": 2, "qty": 3}]) == 6
