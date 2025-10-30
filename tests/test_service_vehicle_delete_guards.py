"""
Deletion guards for vehicles:
- Cannot delete a vehicle currently in 'rented' or 'overdue' status.
- Cannot delete a vehicle if any active rental exists (booked/rented/overdue).
- Deletion is allowed if only finished rentals (e.g., returned) exist.
"""

import pytest

ACTIVE = {"booked", "rented", "overdue"}


@pytest.fixture
def fake_store(monkeypatch):
    """
    Patch services.common._store() to provide isolated in-memory store for guard tests.
    """
    from app.services import common as common_mod

    class Store:
        def __init__(self):
            self.users = {}
            self.vehicles = {}
            self.rentals = {}

    store = Store()
    monkeypatch.setattr(common_mod, "_store", lambda: store)
    return store


def put_vehicle(store, vid=1, status="available"):
    store.vehicles[vid] = {
        "id": vid,
        "brand": "Toyota",
        "model": "Corolla",
        "type": "car",
        "rate": 55.0,
        "status": status,
        "image_path": "",
    }
    return vid


def put_rental(store, rid, vehicle_id, status, start="2030-11-01", end="2030-11-05"):
    store.rentals[rid] = {
        "id": rid,
        "vehicle_id": vehicle_id,
        "renter_id": "u1",
        "start_date": start,
        "end_date": end,
        "status": status,
    }


def test_cannot_delete_vehicle_if_status_rented(fake_store):
    from app.services.vehicle_service import VehicleService
    vid = put_vehicle(fake_store, vid=1, status="rented")
    ok, msg = VehicleService.delete_vehicle(vid, store=fake_store)
    assert not ok
    assert "rented" in msg.lower()


def test_cannot_delete_vehicle_if_status_overdue(fake_store):
    from app.services.vehicle_service import VehicleService
    vid = put_vehicle(fake_store, vid=1, status="overdue")
    ok, msg = VehicleService.delete_vehicle(vid, store=fake_store)
    assert not ok
    assert "overdue" in msg.lower()


def test_cannot_delete_vehicle_if_active_rentals_exist(fake_store):
    from app.services.vehicle_service import VehicleService
    vid = put_vehicle(fake_store, vid=1, status="available")
    put_rental(fake_store, rid=101, vehicle_id=vid, status="rented")
    ok, msg = VehicleService.delete_vehicle(vid, store=fake_store)
    assert not ok
    assert "active" in msg.lower() or "rental" in msg.lower()


def test_can_delete_vehicle_if_only_returned_rentals(fake_store):
    from app.services.vehicle_service import VehicleService
    vid = put_vehicle(fake_store, vid=1, status="available")
    put_rental(fake_store, rid=201, vehicle_id=vid, status="returned")
    ok, msg = VehicleService.delete_vehicle(vid, store=fake_store)
    assert ok, msg
    assert vid not in fake_store.vehicles
