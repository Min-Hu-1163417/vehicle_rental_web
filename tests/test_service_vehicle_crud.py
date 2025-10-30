"""
Unit tests for vehicle admin CRUD operations. Focus on service-layer behavior:
creation assigns an ID and default fields; deletion removes the vehicle when allowed.
"""

import pytest


@pytest.fixture
def fake_store(monkeypatch):
    from app.services.common import Store
    s = Store()
    s.vehicles.clear()
    s.rentals.clear()
    s.users.clear()
    return s


def test_admin_create_and_delete_vehicle(fake_store):
    """
    Creating a vehicle should succeed and assign an ID; deletion should remove it
    if there are no active rentals and status is safe.
    """
    from app.services.vehicle_service import VehicleService

    payload = {
        "brand": "Toyota",
        "model": "Corolla",
        "type": "car",
        "rate": 55.0,
        "image_path": "",
    }

    ok, msg, _ = VehicleService.admin_create_vehicle(payload, store=fake_store)
    assert ok, msg
    assert fake_store.vehicles, "Expected at least one vehicle in the store"
    vid = next(iter(fake_store.vehicles.keys()))
    v = fake_store.vehicles[vid]
    assert v["brand"] == "Toyota"
    assert v["status"] == "available"

    ok, msg = VehicleService.delete_vehicle(vid, store=fake_store)
    assert ok, msg
    assert vid not in fake_store.vehicles
