"""
Cross-booking (overlap) tests for rental creation. Ensures that creating a rental
for a vehicle within a time window overlapping an existing active rental is rejected.
"""

import pytest


@pytest.fixture
def fake_store(monkeypatch):
    """
    Patch services.common._store() to a clean in-memory store.
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


def seed_vehicle(store, vid=1):
    store.vehicles[vid] = {
        "id": vid,
        "brand": "Honda",
        "model": "Fit",
        "type": "car",
        "rate": 40.0,
        "status": "available",
    }
    return vid


def seed_rental(store, rid, vehicle_id, status, start="2030-11-01", end="2030-11-05"):
    store.rentals[rid] = {
        "id": rid,
        "vehicle_id": vehicle_id,
        "renter_id": "u1",
        "start_date": start,
        "end_date": end,
        "status": status,  # 'rented'/'booked' considered active; 'returned' is inactive.
    }


def test_cross_booking_conflict(fake_store):
    """
    Given an existing active rental from 2030-11-01 to 2030-11-05,
    creating a new rental that overlaps (2030-11-03 ~ 2030-11-07) should fail.
    """
    from app.services.rental_service import RentalService

    vid = seed_vehicle(fake_store)
    seed_rental(fake_store, rid=1, vehicle_id=vid, status="rented",
                start="2030-11-01", end="2030-11-05")

    ok, msg = RentalService.create_rental(
        vehicle_id=vid,
        renter_id="u2",
        start_date="2030-11-03",
        end_date="2030-11-07",
    )
    assert not ok
    assert "conflict" in msg.lower() or "overlap" in msg.lower()


def test_non_overlapping_booking_succeeds(fake_store):
    """
    If the new rental is strictly after the existing rental (2030-11-06 ~ 2030-11-10),
    it should succeed.
    """
    from app.services.rental_service import RentalService

    vid = seed_vehicle(fake_store)
    seed_rental(fake_store, rid=1, vehicle_id=vid, status="rented",
                start="2030-11-01", end="2030-11-05")

    ok, msg = RentalService.create_rental(
        vehicle_id=vid,
        renter_id="u3",
        start_date="2030-11-06",
        end_date="2030-11-10",
    )
    assert ok, msg
