# ALVIX - AI-Powered Learning Platform

ALVIX is a Django-based learning platform for students and administrators. It brings course discovery, personalized learning activities, progress tracking, and course administration together in one web application.

## Features

- Student registration, login, profile, assessment, and dashboard workflows
- Course recommendations and AI-assisted course and lesson generation
- Daily lessons, presentations, assignments, and quizzes
- Progress, performance, notifications, and reporting
- Course certificates with PDF download and verification
- Administrative dashboards for users, courses, course levels, and reports

## Technology

- Python and Django
- SQLite for local development
- Django templates, static assets, and uploaded media
- Google Gemini integration for AI-assisted learning features

## Getting started

### Prerequisites

- Python compatible with the Django version used by this project
- The Python packages imported by the application (including Django, `python-dotenv`, `google-genai`, `requests`, `Pillow`, `python-pptx`, and `reportlab`)

This repository does not currently include a Python dependency manifest. Install the application's dependencies in a virtual environment before running it.

### Run locally

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install Django python-dotenv google-genai requests Pillow python-pptx reportlab
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in your browser. The Django admin is available at <http://127.0.0.1:8000/admin/>.

AI and other integrations may require credentials in a local `.env` file. Keep credentials private and do not commit `.env` files. Configure only the environment variables required by the integrations you use.

## Tests

Run the Django test suite with:

```powershell
python manage.py test
```

## Project layout

- `alvix/` - Django project settings and URL configuration
- `alvixapp/` - application models, views, services, migrations, and templates
- `static/`, `public/` - frontend assets
- `media/` - local uploads and generated content
- `manage.py` - Django management entry point
