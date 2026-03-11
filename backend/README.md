# FormIQ Backend

A FastAPI-based backend for the FormIQ application.

## Features

- User authentication and authorization
- Exercise management
- Form check analysis
- Video upload and storage
- RESTful API endpoints

## Requirements

- Python 3.8+
- PostgreSQL
- Redis

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/formiq-app.git
cd formiq-app/backend
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Choose an auth mode and copy the matching env profile:

```bash
# Mode A — local beta (no email required, fastest to start):
cp .env.beta-local .env

# Mode B — real email verification (requires Gmail App Password or Resend.com):
cp .env.beta-email .env
# then edit .env and fill in real MAIL_* values
```

See `docs/beta-auth-modes.md` for the full QA checklist and SMTP setup guide.

Confirm which mode is active (after starting the server):
```bash
curl http://localhost:8000/api/v1/health/health/auth-config
# "deadlock": false → you're good. "deadlock": true → fix .env before inviting users.
```

5. (Legacy) Manual `.env` setup with the following variables:
```env
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=formiq
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
SECRET_KEY=your_secret_key
```

5. Run database migrations:
```bash
alembic upgrade head
```

## Running the Application

1. Start the development server:
```bash
uvicorn app.main:app --reload
```

2. Access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

Run tests with pytest:
```bash
pytest
```

## API Endpoints

### Authentication
- POST `/api/v1/auth/login` - Login user
- POST `/api/v1/auth/refresh` - Refresh access token

### Users
- GET `/api/v1/users/me` - Get current user
- GET `/api/v1/users/` - Get all users
- POST `/api/v1/users/` - Create user
- PUT `/api/v1/users/me` - Update current user
- GET `/api/v1/users/{user_id}` - Get user by ID
- PUT `/api/v1/users/{user_id}` - Update user
- DELETE `/api/v1/users/{user_id}` - Delete user

### Exercises
- GET `/api/v1/exercises/` - Get all exercises
- POST `/api/v1/exercises/` - Create exercise
- GET `/api/v1/exercises/{exercise_id}` - Get exercise by ID
- PUT `/api/v1/exercises/{exercise_id}` - Update exercise
- DELETE `/api/v1/exercises/{exercise_id}` - Delete exercise

### Form Checks
- GET `/api/v1/form-checks/` - Get all form checks
- POST `/api/v1/form-checks/` - Create form check
- GET `/api/v1/form-checks/{form_check_id}` - Get form check by ID
- PUT `/api/v1/form-checks/{form_check_id}` - Update form check
- DELETE `/api/v1/form-checks/{form_check_id}` - Delete form check

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
## Migration Notes

Migrations were consolidated on Tue May  6 12:40:53 PDT 2025. All migration files are now in backend/migrations/versions/.

## Cleanup Notes

Codebase was cleaned up on Tue May  6 12:41:28 PDT 2025. Redundant files have been removed and migrations consolidated.
