"""
Minimal auth flow: register -> login -> access control -> logout.
Adjust route paths if your app uses different endpoints.
"""

import pytest


def _get_session_user_id(client):
    """
    Try to read a login marker from the session. Works for Flask-Login or custom session keys.
    """
    with client.session_transaction() as sess:
        return sess.get("user_id") or sess.get("_user_id")


def _register(client, username, password, role="individual", follow=True):
    return client.post(
        "/auth/register",
        data={"username": username, "password": password, "role": role},
        follow_redirects=follow,
    )


def _login(client, username, password, follow=True):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=follow,
    )


def _logout(client, follow=True):
    return client.get("/auth/logout", follow_redirects=follow)


@pytest.fixture(autouse=True)
def clean_store(monkeypatch):
    """
    Provide a clean in-memory store for each test to avoid crosstalk.
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


def test_register_and_login_then_block_staff_access(client):
    """
    Register an individual user, log in, and verify that staff-only pages are blocked.
    """
    r = _register(client, "alice", "pw123", role="individual")
    assert r.status_code in (200, 302)

    r = _login(client, "alice", "pw123")
    assert r.status_code in (200, 302)
    assert _get_session_user_id(client), "Expected session to contain user id after login"

    r = client.get("/staff/vehicles", follow_redirects=False)
    assert r.status_code in (302, 401, 403)


def test_register_duplicate_username_fails(client):
    """
    Registering the same username twice should fail (return code flexible),
    but response should contain a duplication hint.
    """
    _register(client, "bob", "pw1", role="individual")
    r = _register(client, "bob", "pw2", role="corporate")
    assert r.status_code in (200, 302, 400, 409)
    body = r.get_data(as_text=True).lower()
    assert ("already" in body or "exists" in body or "duplicate" in body), "Expected duplicate username hint"


def test_login_wrong_password(client):
    """
    Logging in with a wrong password should not create a login session and should show an error.
    """
    _register(client, "carl", "pw123", role="individual")
    r = _login(client, "carl", "wrongpw")
    assert r.status_code in (200, 302)
    assert not _get_session_user_id(client)
    body = r.get_data(as_text=True).lower()
    assert ("invalid" in body or "wrong" in body or "fail" in body), "Expected invalid password hint"


def test_staff_login_can_access_staff_pages(client, clean_store):
    """
    If a 'staff' user exists and logs in, they should be able to access /staff/ pages.
    """
    from app.services.user_service import UserService
    ok, msg = UserService.admin_create_user("staffer", "staff", "adminpw")
    assert ok, msg

    r = _login(client, "staffer", "adminpw")
    assert r.status_code in (200, 302)
    assert _get_session_user_id(client)

    r = client.get("/staff/vehicles", follow_redirects=False)
    assert r.status_code in (200, 302)


def test_logout_revokes_access(client, clean_store):
    """
    After logout, staff-only pages should be blocked again.
    """
    from app.services.user_service import UserService
    ok, msg = UserService.admin_create_user("staffer", "staff", "adminpw")
    assert ok, msg

    _login(client, "staffer", "adminpw")
    assert _get_session_user_id(client)

    r = _logout(client)
    assert r.status_code in (200, 302)

    r = client.get("/staff/vehicles", follow_redirects=False)
    assert r.status_code in (302, 401, 403)
