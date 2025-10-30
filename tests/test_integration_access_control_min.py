"""
Minimal integration test to ensure staff-only pages are protected from anonymous access.
This does not require any public /vehicles page and only asserts that protection is active.
"""


def test_staff_pages_require_login(client):
    """
    Anonymous GET to /staff/vehicles should be blocked by login/role checks
    and result in either a redirect (302) or an unauthorized/forbidden status.
    """
    r = client.get("/staff/vehicles")
    assert r.status_code in (302, 401, 403)
