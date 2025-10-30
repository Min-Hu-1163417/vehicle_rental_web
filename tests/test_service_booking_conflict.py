"""
Cross-booking (overlap) tests for rental creation. Ensures that creating a rental
for a vehicle within a time window overlapping an existing active rental is rejected.
"""

import pytest


@pytest.fixture
def fake_store(monkeypatch):
    from app.services.common import Store
    store = Store()
    store.vehicles = {}
    store.rentals = {}
    monkeypatch.setattr("app.services.common.Store.instance", lambda: store)
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

    ok, msg, _ = RentalService.rent(
        renter_id="u2",
        vehicle_id=vid,
        start="2030-11-03",
        end="2030-11-07",
        store=fake_store,
    )
    assert not ok
    assert "conflict" in msg.lower() or "overlap" in msg.lower()


def test_non_overlapping_booking_succeeds(fake_store):
    fake_store.rentals.clear()
    fake_store.vehicles.clear()

    from app.services.rental_service import RentalService

    vid = seed_vehicle(fake_store)
    print("TEST vid:", repr(vid), type(vid))

    seed_rental(fake_store, rid=1, vehicle_id=vid, status="rented",
                start="2030-11-01", end="2030-11-05")

    print("TEST rentals BEFORE:", fake_store.rentals)
    print("TEST vehicles KEYS:", list(fake_store.vehicles.keys()))

    assert len(fake_store.rentals) == 1
    r0 = list(fake_store.rentals.values())[0]
    assert r0["start_date"] == "2030-11-01"
    assert r0["end_date"] == "2030-11-05"
