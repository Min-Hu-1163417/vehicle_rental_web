from app.utils.security import generate_hash, check_hash


def test_password_hash_roundtrip():
    pw = "Secret123"
    h = generate_hash(pw)
    assert check_hash(pw, h)
    assert not check_hash("wrong", h)
