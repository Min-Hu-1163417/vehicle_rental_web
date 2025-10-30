import sys, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest

# If your app exposes create_app(), import it here.
from app import create_app


@pytest.fixture(scope="session")
def app():
    """Create a Flask app configured for testing."""
    os.environ.setdefault("FLASK_ENV", "testing")
    app = create_app()
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        WTF_CSRF_ENABLED=False,  # if you use Flask-WTF
    )
    return app


@pytest.fixture()
def client(app):
    """Anonymous test client."""
    with app.test_client() as c:
        yield c


@pytest.fixture()
def auth_client(client):
    """
    Logged-in client for staff-protected endpoints.
    Adjust the credentials if your seed uses different ones.
    """
    # Login route should create a session cookie.
    r = client.post("/login", data={"username": "admin", "password": "Staff123!"}, follow_redirects=True)
    assert r.status_code in (200, 302)
    return client


@pytest.fixture()
def store_fresh(app):
    """
    Ensure the in-memory Store (if you use one) is fresh and isolated.
    Tries Store.reset(); falls back to clearing common collections.
    """
    try:
        from app.models.store import Store
        st = Store.instance()
        # Prefer a real reset implemented in Store
        if hasattr(st, "reset"):
            st.reset()
        else:
            # Best-effort fallback: clear common attributes if they exist
            for attr in ("users", "vehicles", "rentals", "corporates", "individuals"):
                if hasattr(st, attr):
                    col = getattr(st, attr)
                    if hasattr(col, "clear"):
                        col.clear()
        yield st
        # Teardown
        if hasattr(st, "reset"):
            st.reset()
    except Exception:
        # If no Store or not needed, still yield to keep tests running
        yield None
