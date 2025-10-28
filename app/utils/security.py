from werkzeug.security import generate_password_hash, check_password_hash


def generate_hash(password: str) -> str:
    return generate_password_hash(password)


def check_hash(password: str, hashed: str) -> bool:
    try:
        return check_password_hash(hashed, password)
    except Exception:
        return False
