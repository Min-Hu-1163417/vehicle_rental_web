"""
Unit tests for VehicleService.filter_vehicles: brand/model partial matches,
type filtering, and price range filtering. These tests are pure-service and do not
depend on any HTTP routes or authentication.
"""

import pytest


@pytest.fixture
def fake_store(monkeypatch):
    """
    Patch services.common._store() to return an in-memory fake store for each test.
    This avoids touching global/shared state and keeps tests deterministic.
    """
    from app.services import common as common_mod

    class Store:
        def __init__(self):
            self.users = {}
            self.vehicles = {}
            self.rentals = {}

    store = Store()

    # Seed vehicles
    store.vehicles = {
        1: {"id": 1, "brand": "Toyota", "model": "Corolla", "type": "car", "rate": 55.0, "status": "available"},
        2: {"id": 2, "brand": "Honda",  "model": "Fit",     "type": "car", "rate": 40.0, "status": "available"},
        3: {"id": 3, "brand": "Yamaha", "model": "R3",      "type": "motorbike", "rate": 35.0, "status": "available"},
        4: {"id": 4, "brand": "Isuzu",  "model": "NQR",     "type": "truck", "rate": 150.0, "status": "available"},
    }

    monkeypatch.setattr(common_mod, "_store", lambda: store)
    return store


def test_filter_by_partial_brand(fake_store):
    """
    Should return Toyota when searching by partial brand (case-insensitive).
    """
    from app.services.vehicle_service import VehicleService
    rows = VehicleService.filter_vehicles(brand="toY")
    brands = [r["brand"] for r in rows]
    assert "Toyota" in brands
    assert all(isinstance(r, dict) for r in rows)


def test_filter_by_type(fake_store):
    """
    Should filter by exact type (e.g. 'car') and return only that type.
    """
    from app.services.vehicle_service import VehicleService
    rows = VehicleService.filter_vehicles(vtype="car")
    assert len(rows) >= 2
    assert all(r["type"] == "car" for r in rows)


def test_filter_by_min_max_rate(fake_store):
    """
    Should filter by min/max rate even if inputs are strings (simulating query strings).
    """
    from app.services.vehicle_service import VehicleService
    rows = VehicleService.filter_vehicles(min_rate="50", max_rate="200")
    rates = [r["rate"] for r in rows]
    assert rates, "Expected at least one vehicle in range"
    assert all(50.0 <= rate <= 200.0 for rate in rates)


def test_filter_with_empty_params_returns_all(fake_store):
    """
    Empty inputs should not crash and should return all vehicles.
    """
    from app.services.vehicle_service import VehicleService
    rows = VehicleService.filter_vehicles(brand=None, vtype=None, min_rate=None, max_rate=None)
    assert len(rows) == len(fake_store.vehicles)


def test_filter_ignores_invalid_min_max(fake_store):
    """
    Invalid min/max values should be safely ignored instead of raising.
    """
    from app.services.vehicle_service import VehicleService
    rows = VehicleService.filter_vehicles(min_rate="not-a-number", max_rate="n/a")
    assert len(rows) == len(fake_store.vehicles)
