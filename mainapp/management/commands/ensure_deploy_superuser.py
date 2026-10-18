import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create the configured deployment superuser if it does not already exist.'

    def handle(self, *args, **options):
        username = os.getenv('DJANGO_SUPERUSER_USERNAME')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD')
        if not username and not password:
            self.stdout.write('Deployment superuser credentials are not configured; skipping.')
            return
        if not username or not password:
            raise CommandError(
                'Both DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD must be configured.'
            )

        user_model = get_user_model()
        username_field = user_model.USERNAME_FIELD
        manager = user_model._default_manager.db_manager('default')
        existing_user = manager.filter(**{username_field: username}).first()
        if existing_user is not None:
            if not existing_user.is_superuser:
                raise CommandError(
                    'The configured deployment username already exists but is not a superuser; '
                    'no account changes were made.'
                )
            self.stdout.write('The configured deployment superuser already exists; no changes were made.')
            return

        candidate = user_model(**{username_field: username})
        try:
            validate_password(password, user=candidate)
        except ValidationError as exc:
            raise CommandError('The configured deployment password does not meet password requirements.') from exc

        manager.create_superuser(**{username_field: username}, password=password)
        self.stdout.write('Deployment superuser created successfully.')
