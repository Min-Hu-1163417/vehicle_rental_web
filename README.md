# Vehicle Rental Web — Educational Scaffold (Patched)

**For learning only. Do not submit as coursework.**

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seeds.py    # sets admin password and adds demo vehicles
python run.py
# Open http://127.0.0.1:5000
# Login as admin/admin123, then add vehicles/users in Staff panel
```

## Staff role

- Run `python seeds.py` then login as **admin/admin123**.
- In **Manage Users**, you can now create users with role **staff** (for demo/testing).

## Staff role (policy)

- Staff **cannot** be self-registered or created from the Admin UI. This is intentional and aligns with least-privilege.
- Run `python seeds.py` to provision the default Staff admin, then login with:
    - **username**: `admin`
    - **password**: `admin123`
- This seeded admin is the only Staff account for demo/testing.
