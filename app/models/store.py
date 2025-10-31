import atexit
import os
import pickle
import threading
import uuid
from pathlib import Path
from app.utils.security import generate_hash

# ---- Paths ----
BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = BASE_DIR / "data.pkl"


class Store:
    _inst = None
    _inst_lock = threading.Lock()
    _atexit_registered = False

    def __init__(self, path: str | os.PathLike | None = None):
        self.path = str(path or DEFAULT_DATA_PATH)
        self.users: dict[str, dict] = {}
        self.vehicles: dict[str, dict] = {}
        self.rentals: dict[str, dict] = {}
        self._rw = threading.RLock()

        print(f"[Store] Using file: {self.path}")
        self._load()

        # Default staff account:
        # Created only when the file does not exist or is empty
        # (to avoid conflicts with seeded or test data)
        if not os.path.exists(self.path) or (not self.users and not self.vehicles and not self.rentals):
            if not any(u.get("role") == "staff" for u in self.users.values()):
                rid = str(uuid.uuid4())
                self.users[rid] = {
                    "renter_id": rid,
                    "username": "staff",
                    "password_hash": generate_hash("Staff123"),
                    "role": "staff",
                }
                self._dump()

        # Automatically save on exit (skipped in test environments)
        if not Store._atexit_registered and os.getenv("APP_ENV") != "test":
            atexit.register(self.save)
            Store._atexit_registered = True

    # ---------- Singleton ----------
    @classmethod
    def instance(cls, path: str | os.PathLike | None = None):
        """Return the global singleton instance of Store."""
        with cls._inst_lock:
            if cls._inst is None:
                cls._inst = Store(path or DEFAULT_DATA_PATH)
        return cls._inst

    @classmethod
    def _store(cls):
        """Backward compatibility alias for instance()."""
        return cls.instance()

    # ---------- Persistence ----------
    def _load(self):
        """Load data from the pickle file, or start empty if unavailable or invalid."""
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "rb") as f:
                data = pickle.load(f)
        except Exception as e:
            print(f"[Store] Load failed ({e}); starting empty.")
            return

        if isinstance(data, dict):
            self.users = data.get("users", {}) or {}
            self.vehicles = data.get("vehicles", {}) or {}
            self.rentals = data.get("rentals", {}) or {}
            print(
                f"[Store] Loaded: users={len(self.users)}, vehicles={len(self.vehicles)}, rentals={len(self.rentals)}")
        else:
            # Handle incompatible data format: backup the old file and start empty
            try:
                bak = self.path + ".bak"
                os.replace(self.path, bak)
                print(f"[Store] Incompatible store ({type(data).__name__}); backed up to {bak}. Starting empty.")
            except Exception as e:
                print(f"[Store] Backup failed: {e}")

    def _dump(self):
        """Write the in-memory data to the pickle file safely (atomic replace)."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        payload = {
            "users": self.users,
            "vehicles": self.vehicles,
            "rentals": self.rentals,
        }
        with open(tmp, "wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    def save(self):
        """Thread-safe save method."""
        with self._rw:
            print(f"[Store] Saving to {self.path} ...")
            self._dump()

    # ---------- Users ----------
    def user_exists(self, username: str) -> bool:
        """Return True if the given username already exists."""
        return any(u["username"] == username for u in self.users.values())

    def find_user(self, username: str) -> dict | None:
        """Find a user by username."""
        for u in self.users.values():
            if u["username"] == username:
                return u
        return None

    def get_user(self, renter_id: str) -> dict | None:
        """Get user data by renter_id."""
        return self.users.get(renter_id)

    def create_user(self, username: str, password_hash: str, role: str) -> str:
        """Create a new user and return its ID."""
        with self._rw:
            if self.user_exists(username):
                raise ValueError("Username already exists")
            rid = str(uuid.uuid4())
            self.users[rid] = {
                "renter_id": rid,
                "username": username,
                "password_hash": password_hash,
                "role": role,
            }
            self._dump()
            return rid

    def delete_user(self, renter_id: str) -> bool:
        """Delete a user by ID."""
        with self._rw:
            if renter_id in self.users:
                del self.users[renter_id]
                self._dump()
                return True
            return False

    # ---------- Vehicles ----------
    def create_vehicle(self, data: dict) -> str:
        """Create a new vehicle record and return its ID."""
        with self._rw:
            vid = str(uuid.uuid4())
            self.vehicles[vid] = {
                "vehicle_id": vid,
                "brand": data.get("brand", ""),
                "model": data.get("model", ""),
                "type": data.get("type", "car"),
                "rate": float(data.get("rate") or 0),
                "status": data.get("status", "available"),
                "image_path": data.get("image_path", "/static/images/placeholder.png"),
            }
            self._dump()
            return vid

    def get_vehicle(self, vehicle_id: str) -> dict | None:
        """Get vehicle information by ID."""
        return self.vehicles.get(str(vehicle_id))

    def update_vehicle(self, vehicle_id: str, **updates) -> bool:
        """Update vehicle attributes; return True if updated successfully."""
        with self._rw:
            vid = str(vehicle_id)
            if vid not in self.vehicles:
                return False
            v = self.vehicles[vid]
            if "rate" in updates:
                try:
                    updates["rate"] = float(updates["rate"])
                except (TypeError, ValueError):
                    return False
            if "image_path" in updates:
                val = updates.get("image_path") or ""
                updates["image_path"] = val.strip() or "/static/images/placeholder.png"
            v.update({k: v2 for k, v2 in updates.items() if v2 is not None})
            self._dump()
            return True

    def delete_vehicle(self, vehicle_id: str) -> bool:
        """Delete a vehicle by ID."""
        with self._rw:
            if vehicle_id in self.vehicles:
                del self.vehicles[vehicle_id]
                self._dump()
                return True
            return False

    # ---------- Rentals ----------
    def create_rental(self, r: dict) -> str:
        """Create a new rental record."""
        with self._rw:
            rid = str(uuid.uuid4())
            r = dict(r)
            r["rental_id"] = rid
            self.rentals[rid] = r
            self._dump()
            return rid

    def update_rental(self, rid: str, updates: dict) -> bool:
        """Update an existing rental by ID."""
        with self._rw:
            if rid in self.rentals:
                self.rentals[rid].update(updates)
                self._dump()
                return True
            return False


# Backward compatibility for old imports:
# from app.services.common import _store
def _store():
    return Store.instance()
