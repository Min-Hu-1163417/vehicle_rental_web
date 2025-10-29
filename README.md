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
│       ├── test_integration_smoke.py
│       ├── test_rent_availability.py
│       ├── test_unit_auth.py
│       └── test_unit_discounts.py
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

## 🧠 Tech Stack

| Layer    | Technology                      |
|----------|---------------------------------|
| Backend  | Flask (Python 3.x)              |
| Frontend | HTML5, Bootstrap 5, Jinja2      |
| Storage  | Pickle-based store (`data.pkl`) |
| Testing  | Pytest                          |

---

## 📦 Key Business Logic

* **Overdue detection** → automatically marks rentals as overdue if end date < today
* **Access control** → decorators restrict staff-only actions
* **Error handling** → custom exception classes for clarity
* **Date handling** → time zone aware (Pacific/Auckland)

---

## 🧑‍💻 Author

**Vincent Hu**
Master of Applied Computing, Lincoln University
📍 Christchurch, New Zealand
📧 [vincent.hu@outlook.co.nz](mailto:vincent.hu@outlook.co.nz)
🌐 [GitHub Profile](https://github.com/Min-Hu-1163417/vehicle_rental_web.git)

---

### 🪪 License

This project is for educational use only and is not intended for commercial deployment.
