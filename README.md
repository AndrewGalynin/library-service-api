# Library Service API

An online RESTful management system for library inventory, book borrowings, customer accounts, automated Telegram notifications, and Stripe online payments built with Django REST Framework.

## Features

- **Users Service:** Custom `User` model with email-based authentication, JWT token management (`SimpleJWT`), user registration, and profile management (`/api/users/me/`).
- **Books Service:** Full CRUD for library books (`HARD` / `SOFT` covers, inventory tracking, daily rental fees in USD) with public read access and admin-only write permissions.
- **Borrowings Service:** Atomic book borrowing (`inventory -= 1`), role-based filtering (`?is_active=true/false`, `?user_id=...`), and a custom book return endpoint (`POST /api/borrowings/<id>/return/`) that restores inventory and calculates overdue fines.
- **Notifications Service:** Asynchronous Telegram notifications via **Django Q** (`django-q2`) for new borrowings, successful payments, and scheduled daily overdue borrowing reports.
- **Payments Service:** **Stripe Checkout** integration for borrowing fees (`PAYMENT`) and overdue fines (`FINE`) with payment verification callbacks (`/api/payments/success/`, `/api/payments/cancel/`).
- **API Documentation:** Interactive OpenAPI 3.0 documentation via **Swagger UI** and **ReDoc** (`drf-spectacular`).

## Tech Stack

- Python 3.12+ / Django / Django REST Framework
- `djangorestframework-simplejwt` (JWT Authentication)
- `django-q2` (Background & scheduled task worker)
- `stripe` (Payment processing)
- `drf-spectacular` (OpenAPI / Swagger documentation)
- SQLite (Default local database)

## Local Setup & Installation

### 1. Clone the repository and activate virtual environment

```bash
git clone [https://github.com/AndrewGalynin/library-service-api.git](https://github.com/AndrewGalynin/library-service-api.git)
cd library-service-api
python -m venv .venv
source .venv/Scripts/activate  # Windows (Git Bash)
# .venv\Scripts\activate       # Windows (CMD/PowerShell)
# source .venv/bin/activate    # Linux/macOS
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the root directory based on `.env.example`:

```env
SECRET_KEY='your-django-secret-key'
DEBUG=True
TELEGRAM_BOT_TOKEN='your-telegram-bot-token'
TELEGRAM_CHAT_ID='your-telegram-chat-id'
STRIPE_SECRET_KEY='sk_test_your-stripe-secret-key'
```

### 4. Apply migrations and create a superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Register periodic background tasks

```bash
python manage.py setup_periodic_tasks
```

### 6. Run the application

Start the Django development server in one terminal:

```bash
python manage.py runserver
```

Start the Django Q background worker in a second terminal:

```bash
python manage.py qcluster
```

## API Documentation & Key Endpoints

Once the server is running, access the interactive API documentation:

- **Swagger UI:** `http://127.0.0.1:8000/api/doc/swagger/`
- **ReDoc:** `http://127.0.0.1:8000/api/doc/redoc/`
- **OpenAPI Schema:** `http://127.0.0.1:8000/api/doc/`

### Main Endpoints Overview

| Service | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Users** | `POST` | `/api/users/` | Register a new customer |
| **Users** | `POST` | `/api/users/token/` | Obtain JWT access & refresh tokens |
| **Users** | `POST` | `/api/users/token/refresh/` | Refresh JWT access token |
| **Users** | `GET, PUT, PATCH` | `/api/users/me/` | View or update current user profile |
| **Books** | `GET, POST` | `/api/books/` | List books (public) or add a new book (admin) |
| **Books** | `GET, PUT, PATCH, DELETE` | `/api/books/<id>/` | Retrieve, update, or delete a book |
| **Borrowings** | `GET, POST` | `/api/borrowings/` | List borrowings (supports `?is_active=` & `?user_id=`) or borrow a book |
| **Borrowings** | `GET` | `/api/borrowings/<id>/` | Retrieve borrowing details |
| **Borrowings** | `POST` | `/api/borrowings/<id>/return/` | Return a borrowed book and update inventory |
| **Payments** | `GET` | `/api/payments/` | List user payments (or all payments for admins) |
| **Payments** | `GET` | `/api/payments/success/?session_id=...` | Verify completed Stripe Checkout session |
| **Payments** | `GET` | `/api/payments/cancel/` | Handle paused/cancelled Stripe payment |
