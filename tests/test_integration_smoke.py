import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test")
    with app.test_client() as c:
        yield c


def test_home(client):
    r = client.get("/")
    assert r.status_code == 200
