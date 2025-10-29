from app import create_app
from app.models.store import Store
from app.utils.security import generate_hash


def ensure_user(store: Store, username: str, password: str, role: str):
    """
    Ensure a user with `username` exists in the store.
    - If exists: update password hash and role (idempotent).
    - If not:   create a new user.
    """
    u = store.find_user(username)
    if u:
        u["password_hash"] = generate_hash(password)
        u["role"] = role
        return u["renter_id"]
    else:
        return store.create_user(username, generate_hash(password), role)


def main():
    app = create_app()
    with app.app_context():
        store = Store.instance()

        # ---- Staff / Customer / Corporate demo accounts ----
        ensure_user(store, "staff", "Staff123", "staff")
        ensure_user(store, "customer", "Customer123", "customer")
        ensure_user(store, "corporate", "Corporate123", "corporate")

        # ---- Demo vehicles (create only if none exist) ----
        if not store.vehicles:
            store.create_vehicle({
                "brand": "Toyota", "model": "Corolla", "type": "car", "rate": 45,
                "image_path": "/static/images/corolla.jpg", "status": "available",
            })
            store.create_vehicle({
                "brand": "Honda", "model": "Civic", "type": "car", "rate": 50,
                "image_path": "/static/images/civic.jpg", "status": "available",
            })
            store.create_vehicle({
                "brand": "Yamaha", "model": "MT-07", "type": "motorbike", "rate": 40,
                "image_path": "/static/images/yamaha.jpg", "status": "available",
            })
            store.create_vehicle({
                "brand": "Isuzu", "model": "N-Series", "type": "truck", "rate": 95,
                "image_path": "/static/images/isuzu.jpg", "status": "available",
            })

        store.save()

        print("✅ Seed complete.")
        print("🔑 Staff login:     staff / Staff123")
        print("👤 Customer login:  customer / Customer123")
        print("🏢 Corporate login: corporate / Corporate123")


if __name__ == "__main__":
    main()
