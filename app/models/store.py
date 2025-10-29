import atexit
import os
import pickle
import threading
import uuid
from app.utils.security import generate_hash

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
DEFAULT_DATA_PATH = os.path.join(BASE_DIR, "data.pkl")


class Store:
    _inst = None
    _inst_lock = threading.Lock()

    def __init__(self, path: str | None = None):
        # use a stable absolute path
        self.path = path or DEFAULT_DATA_PATH
        self.users = {}
        self.vehicles = {}
        self.rentals = {}
        self._rw = threading.RLock()
        self._load()

        # ensure at least one staff user exists
        if not any(u.get("role") == "staff" for u in self.users.values()):
            rid = str(uuid.uuid4())
            self.users[rid] = {
                "renter_id": rid,
                "username": "staff",
                "password_hash": generate_hash("Staff123"),
                "role": "staff",
            }
        atexit.register(self.save)

    @classmethod
    def instance(cls, path: str | None = None):
        with cls._inst_lock:
            if cls._inst is None:
                cls._inst = Store(path or DEFAULT_DATA_PATH)
        return cls._inst

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "rb") as f:
                data = pickle.load(f)
                self.users = data.get("users", {})
                self.vehicles = data.get("vehicles", {})
                self.rentals = data.get("rentals", {})

    def _dump(self):
        tmp = self.path + ".tmp"
        with open(tmp, "wb") as f:
            pickle.dump({
                "users": self.users,
                "vehicles": self.vehicles,
                "rentals": self.rentals,
            }, f)
        os.replace(tmp, self.path)

    def save(self):
        with self._rw:
            self._dump()

    # Users
    def user_exists(self, username):
        return any(u["username"] == username for u in self.users.values())

    def find_user(self, username):
        for u in self.users.values():
            if u["username"] == username:
                return u
        return None

    def get_user(self, renter_id):
        return self.users.get(renter_id)

    def create_user(self, username, password_hash, role):
        with self._rw:
            rid = str(uuid.uuid4())
            self.users[rid] = {
                "renter_id": rid,
                "username": username,
                "password_hash": password_hash,
                "role": role,
            }
            self.save()
            return rid

    def delete_user(self, renter_id):
        with self._rw:
            if renter_id in self.users:
                del self.users[renter_id]
                self.save()
                return True
            return False

    # Vehicles
    def create_vehicle(self, data):
        with self._rw:
            vid = str(uuid.uuid4())
            self.vehicles[vid] = {
                "vehicle_id": vid,
                "brand": data.get("brand", ""),
                "model": data.get("model", ""),
                "type": data.get("type", "car"),
                "rate": float(data.get("rate") or 0),
                "image_path": data.get("image_path", "/static/images/placeholder.png"),
            }
            self.save()
            return vid

    def delete_vehicle(self, vehicle_id):
        with self._rw:
            if vehicle_id in self.vehicles:
                del self.vehicles[vehicle_id]
                self.save()
                return True
            return False

    # Rentals
    def create_rental(self, r):
        with self._rw:
            rid = str(uuid.uuid4())
            r["rental_id"] = rid
            self.rentals[rid] = r
            self.save()
            return rid

    def update_rental(self, rid, updates):
        with self._rw:
            if rid in self.rentals:
                self.rentals[rid].update(updates)
                self.save()
                return True
            return False
