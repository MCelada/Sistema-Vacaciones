## Corporate Vacation & Leave Management System

### Tech Stack
- Backend: Django 5, DRF, SimpleJWT, PostgreSQL (SQLite by default for dev)
- Frontend: React (Vite + TypeScript)

### Prerequisites
- Python 3.12+
- Node.js 20.19+ (for frontend)
- PostgreSQL 14+ (optional for dev; default uses SQLite)

### Backend Setup
```
cd backend
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt  # if present; otherwise see below
```

If no requirements.txt:
```
pip install django djangorestframework djangorestframework-simplejwt psycopg2-binary django-cors-headers
```

Environment variables for PostgreSQL (optional):
```
export DB_ENGINE=django.db.backends.postgresql
export DB_NAME=vacaciones
export DB_USER=vacaciones
export DB_PASSWORD=secret
export DB_HOST=localhost
export DB_PORT=5432
```

Run migrations and admin:
```
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

JWT Auth endpoints:
- POST `/api/auth/token/` { email, password }
- POST `/api/auth/token/refresh/` { refresh }

API collections:
- `/api/employees/`
- `/api/policies/`
- `/api/holidays/`
- `/api/balances/` and `/api/balances/current/`
- `/api/requests/` with actions: `POST /:id/approve`, `POST /:id/reject`
- Account: `/api/me/`

Management commands:
```
python manage.py annual_allotment --year 2025
python manage.py carry_over --year 2025
```

### Frontend Setup
Requires Node.js 20.19+.
```
cd frontend
npm install
npm run dev
```

### Notes
- Email backend is console in dev; configure SMTP in settings for production.
- Timezone set to `America/Argentina/Buenos_Aires` and language `es-ar`.

