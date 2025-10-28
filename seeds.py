from app import create_app
from app.models.store import Store
from app.utils.security import generate_hash


def main():
    app = create_app()
    with app.app_context():
        store = Store.instance()
        # Set admin password to 'admin123'
        for u in store.users.values():
            if u.get("username") == "staff":
                u["password_hash"] = generate_hash("Staff123")
                break
        # Add demo vehicles if none
        if not store.vehicles:
            store.create_vehicle({"brand": "Toyota", "model": "Corolla", "type": "car", "rate": 45,
                                  "image_path": "/static/images/corolla.jpg", 'status': 'available'})
            store.create_vehicle({"brand": "Honda", "model": "Civic", "type": "car", "rate": 50,
                                  "image_path": "/static/images/civic.jpg", 'status': 'available'})
            store.create_vehicle({"brand": "Yamaha", "model": "MT-07", "type": "motorbike", "rate": 40,
                                  "image_path": "/static/images/yamaha.jpg", 'status': 'available'})
            store.create_vehicle({"brand": "Isuzu", "model": "N-Series", "type": "truck", "rate": 95,
                                  "image_path": "/static/images/isuzu.jpg", 'status': 'available'})
        store.save()
        print("Seed complete. Staff login: staff / Staff123")


if __name__ == "__main__":
    main()
