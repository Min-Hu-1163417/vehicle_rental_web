# 🚗 Vehicle Rental Web System

A **Flask-based vehicle rental management web application**, designed for educational and demonstration purposes.  
It allows users to browse, rent, and return vehicles, while staff can manage vehicles, users, and rental records.

---

## 🧩 Features

### 👤 User Portal

- Register / login authentication
- Browse available vehicles
- Filter by type, brand, or rate
- Submit rental requests and view booking history

### 🧑‍💼 Staff Dashboard

- Manage vehicles (add / delete / view details)
- Track overdue rentals and availability status
- View user rental history and analytics

### ⚙️ System Logic

- MVC-style structure (Controllers → Services → Models)
- Data persistence via `data.pkl` store
- Automatic overdue detection based on end date
- Reusable templates with Jinja2

---

## 🏗️ Project Structure

```text
vehicle_rental_web/
├── app/
│   ├── controllers/          # Flask route controllers (view logic)
│   │   ├── auth.py           # User login & registration
│   │   ├── rentals.py        # Rental operations (rent/return)
│   │   ├── staff.py          # Staff dashboard routes
│   │   └── views.py          # Public and shared views
│   │
│   ├── models/               # Simple data models & in-memory store
│   │   ├── store.py          # Singleton storage for users, vehicles, rentals
│   │   ├── user.py           # User model definitions
│   │   └── vehicle.py        # Vehicle entity definitions
│   │
│   ├── services/             # Business logic layer
│   │   ├── analytics_service.py  # Dashboard analytics
│   │   ├── common.py             # Shared utility functions
│   │   ├── rental_service.py     # Handle rental creation & return
│   │   ├── user_service.py       # User management logic
│   │   ├── vehicle_service.py    # Vehicle management + overdue logic
│   │   └── __init__.py
│   │
│   ├── static/               # Static frontend resources
│   │   ├── css/style.css
│   │   └── images/           # Placeholder and sample images
│   │
│   ├── templates/            # HTML templates (Jinja2)
│   │   ├── auth/             # Login / Register pages
│   │   ├── dashboards/       # Dashboards for different user roles
│   │   ├── layouts/          # Base layout (extends mechanism)
│   │   ├── partials/         # Reusable UI fragments
│   │   ├── users/            # Staff analytics, invoices
│   │   └── vehicles/         # Vehicle listing & details
│   │
│   ├── utils/                # Utility modules
│   │   ├── constants.py      # Enumerations and constants
│   │   ├── decorators.py     # Route decorators for role-based access
│   │   ├── filters.py        # Jinja2 template filters
│   │   ├── security.py       # Password hashing, login helpers
│   │   └── exceptions.py     # Custom exception classes
│   │
│   └── tests/                # Unit & integration tests
│       ├── conftest.py
│       ├── test_integration_access_control_min.py
│       ├── test_integration_auth_flow.py
│       ├── test_service_booking_conflict.py
│       ├── test_service_vehicle_crud.py
│	    ├── test_service_vehicle_delete_guards.py
│	    └── test_service_vehicle_filter.py
│
├── data.pkl                  # Local data persistence
├── requirements.txt          # Python dependencies
├── run.py                    # Flask entry point
├── reset_data.py             # Script to reset data.pkl
├── seeds.py                  # Initial data seeding script
├── README.md                 # Project documentation
└── .gitignore
````

---

## 🚀 Getting Started

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Initialize Seed Data

Before the first run, execute the seeding script to populate sample users and vehicles:

```bash
python seeds.py
```

### 3️⃣ Run the App

```bash
python run.py
```

### 4️⃣ Access in Browser

👉 [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

Default users (from seed data):

* **Staff:** `staff / Staff123`
* **Customer:** `customer / Customer123`
* **Corporate:** `corporate / Corporate123`

### 5️⃣ Reset Data (Optional)

To start fresh with a clean dataset, simply stop the app and rerun the setup sequence:

```bash
python reset_data.py
python seeds.py
python run.py
```

---

# 🧪 Tests

This project uses **pytest** for unit and integration testing.
All tests are located in the `tests/` directory and are designed to verify the correctness, reliability, and safety of
both the **service layer** and **authentication logic**.

## 📂 Test File Overview

| File                                         | Purpose                                                                                                                                                               |
|----------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`conftest.py`**                            | Defines shared pytest fixtures, such as `fake_store`, which provides an in-memory store for isolated testing. This ensures tests do not modify real application data. |
| **`test_integration_access_control_min.py`** | Minimal access control integration tests. Verifies that non-staff users cannot access staff-only routes (e.g., `/staff/vehicles`).                                    |
| **`test_integration_auth_flow.py`**          | Tests the authentication flow: user registration, login, session handling, and logout. Ensures proper redirects and session persistence.                              |
| **`test_service_booking_conflict.py`**       | Verifies booking conflict logic: prevents overlapping rentals for the same vehicle.                                                                                   |
| **`test_service_vehicle_crud.py`**           | Tests vehicle creation, retrieval, update, and deletion at the service layer. Ensures that CRUD operations work as expected.                                          |
| **`test_service_vehicle_delete_guards.py`**  | Checks deletion guards — vehicles in *rented* or *overdue* status, or referenced by active rentals, cannot be deleted.                                                |
| **`test_service_vehicle_filter.py`**         | Tests vehicle filtering logic, including case-insensitive brand/model matching, type filtering, and numeric range filtering (with invalid input tolerance).           |

---

## 🎯 Testing Goals

The goal of the test suite is to ensure:

1. **Business rules are correctly enforced** (e.g., deletion and booking guards).
2. **User flows work as expected** — login, logout, and access control.
3. **Filtering and validation logic** handle both normal and invalid inputs gracefully.
4. **Data integrity** is maintained (no cross-test interference, thanks to isolated `fake_store` fixtures).

In short, the tests guarantee that the application’s backend behaves correctly, even under invalid or unexpected
conditions.

---

## ▶️ How to Run the Tests

1. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # macOS/Linux
   # .venv\Scripts\activate       # Windows
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements-dev.txt
   ```

   (If no file exists, at least install pytest:)

   ```bash
   pip install pytest
   ```

3. **Run all tests:**

   ```bash
   pytest
   ```

4. **Run with verbose output:**

   ```bash
   pytest -v
   ```

5. **Run a single file or test:**

   ```bash
   pytest tests/test_service_vehicle_filter.py
   pytest tests/test_service_vehicle_filter.py::test_filter_by_partial_brand -vv
   ```

6. **Generate a coverage report (optional):**

   ```bash
   pytest --cov=app --cov-report=term-missing
   ```

---

## ✅ Expected Results

* All tests should **pass without modifying any real data**.
* The suite should complete quickly (<3 seconds) since all data lives in memory.
* Failures (if any) will help identify missing validations or broken business logic.

---

## 🧠 Tech Stack

| Layer    | Technology                      |
|----------|---------------------------------|
| Backend  | Flask (Python 3.x)              |
| Frontend | HTML5, Bootstrap 5, Jinja2      |
| Storage  | Pickle-based store (`data.pkl`) |
| Testing  | Pytest                          |

---

## 📦 Key Logic

* **Overdue detection** → automatically marks rentals as overdue if end date < today
* **Access control** → decorators restrict staff-only actions
* **Error handling** → custom exception classes for clarity
* **Date handling** → time zone aware (Pacific/Auckland)

---

## 🧑‍💻 Author

**Vincent Hu, 1163417**<br>

🏫 Master of Applied Computing, Lincoln University<br>
📍 Christchurch, New Zealand<br>
📧 [vincent.hu@lincolnuni.ac.nz](mailto:vincent.hu@lincolnuni.ac.nz)<br>
🌐 [GitHub Profile](https://github.com/Min-Hu-1163417/vehicle_rental_web.git)

---

### 🪪 License

This project is for educational use only and is not intended for commercial deployment.
