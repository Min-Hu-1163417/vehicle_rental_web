import sys, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest

from app import create_app


@pytest.fixture(autouse=True)
def reset_store_between_tests():
    try:
        from app.services.common import _store
        st = _store()
        if hasattr(st, "users"):    st.users.clear()
        if hasattr(st, "vehicles"): st.vehicles.clear()
        if hasattr(st, "rentals"):  st.rentals.clear()
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True)
def unified_store(monkeypatch):
    """
    Provide a single in-memory store and patch _store() in common + each service
    module to return the SAME object. This avoids 'Vehicle not found' due to
    module-level aliasing or separate instances.
    """
    from app.services import common as common_mod

    class Store:
        def __init__(self):
            self.users = {}
            self.vehicles = {}
            self.rentals = {}

    store = Store()

    # Patch common._store
    monkeypatch.setattr(common_mod, "_store", lambda: store, raising=True)

    # Also patch aliases imported in service modules (if they did "from common import _store")
    try:
        from app.services import vehicle_service as vs
        monkeypatch.setattr(vs, "_store", lambda: store, raising=False)
    except Exception:
        pass

    try:
        from app.services import user_service as us
        monkeypatch.setattr(us, "_store", lambda: store, raising=False)
    except Exception:
        pass

    try:
        from app.services import rental_service as rs
        monkeypatch.setattr(rs, "_store", lambda: store, raising=False)
    except Exception:
        pass

    yield store


@pytest.fixture
def client():
    """
    Minimal Flask test client if you have app factory.
    Adjust import to your actual create_app.
    """
    from app import create_app
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, LOGIN_DISABLED=False)
    with app.test_client() as c:
        yield c
