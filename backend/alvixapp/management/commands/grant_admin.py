"""Grant (or revoke) ALVIX administrator rights: python manage.py grant_admin <email-or-username> [--revoke]"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q


class Command(BaseCommand):
    help = "Make an existing account an ALVIX administrator (Django staff), or revoke it with --revoke."

    def add_arguments(self, parser):
        parser.add_argument('identifier', help='email address or username of an existing account')
        parser.add_argument('--revoke', action='store_true', help='remove administrator rights')

    def handle(self, identifier, revoke=False, **options):
        users = User.objects.filter(Q(email__iexact=identifier) | Q(username__iexact=identifier))
        if users.count() != 1:
            raise CommandError(f"Expected exactly one account matching '{identifier}', found {users.count()}.")
        user = users.get()
        user.is_staff = not revoke
        user.save(update_fields=['is_staff'])
        state = 'revoked from' if revoke else 'granted to'
        self.stdout.write(self.style.SUCCESS(f"Administrator rights {state} {user.username} <{user.email}>."))
