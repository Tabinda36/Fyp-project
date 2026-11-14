"""Create or update an ALVIX administrator account (idempotent).

    python manage.py seed_admin --email admin@example.com --password "..."

Falls back to ALVIX_SEED_ADMIN_EMAIL / ALVIX_SEED_ADMIN_PASSWORD from the environment.
Running it again resets the password and keeps the account an administrator; no data is deleted.
"""

import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from alvixapp.models import Profile


class Command(BaseCommand):
    help = "Create (or update) an administrator account that logs in with the given email and password."

    def add_arguments(self, parser):
        parser.add_argument('--email', default=os.environ.get('ALVIX_SEED_ADMIN_EMAIL', ''))
        parser.add_argument('--password', default=os.environ.get('ALVIX_SEED_ADMIN_PASSWORD', ''))
        parser.add_argument('--name', default='', help='full name shown in the app (default: part of the email before @)')

    @transaction.atomic
    def handle(self, email, password, name, **options):
        email = (email or '').strip().lower()
        if not email or '@' not in email:
            raise CommandError('Give a valid --email (or set ALVIX_SEED_ADMIN_EMAIL).')
        if not password:
            raise CommandError('Give --password (or set ALVIX_SEED_ADMIN_PASSWORD).')

        matches = User.objects.filter(email__iexact=email)
        if matches.count() > 1:
            raise CommandError(f'{matches.count()} accounts share {email}; fix that before seeding.')
        user = matches.first()
        created = user is None
        if created:
            base = email.split('@')[0][:140] or 'admin'
            username, n = base, 1
            while User.objects.filter(username__iexact=username).exists():
                n += 1
                username = f'{base}{n}'
            user = User(username=username)

        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if name or not user.first_name:
            user.first_name = name or email.split('@')[0]
        user.set_password(password)
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        if not profile.full_name:
            profile.full_name = user.first_name
            profile.save()

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} administrator {user.username} <{user.email}> (staff + superuser).'))
