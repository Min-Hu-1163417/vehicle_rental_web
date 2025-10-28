from app.models.service import Service


def test_discounts():
    assert Service._calc_discount("corporate", 3) == 0.15
    assert Service._calc_discount("individual", 3) == 0.0
    assert Service._calc_discount("individual", 7) == 0.10
