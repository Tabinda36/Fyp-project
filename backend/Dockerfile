# ALVIX backend (Django + DRF) — production image for Railway (or any Docker host).
# Build context: backend/   ->   docker build -t alvix-backend backend
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System libraries: cairo/pango for xhtml2pdf (PDF certificates), build tools for any
# package without a wheel, libpq for psycopg, fonts for PDF/PPT rendering.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential pkg-config \
        libcairo2-dev libpango1.0-dev libjpeg62-turbo-dev zlib1g-dev libffi-dev \
        libpq5 fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Static files are collected at build time (served by WhiteNoise). Settings require a secret
# key, so a throwaway one is used only for this step.
RUN DJANGO_SECRET_KEY=build-only-not-secret DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 alvix \
    && mkdir -p /app/media \
    && chown -R alvix:alvix /app
USER alvix

ENV PORT=8000
EXPOSE 8000

# Apply migrations, then serve. Long timeout: AI course generation can take a while.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn alvix.wsgi:application --bind 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --worker-class gthread --timeout ${GUNICORN_TIMEOUT:-300} --access-logfile - --error-logfile -"]
