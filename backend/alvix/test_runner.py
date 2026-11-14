"""Test runner that disables all external AI/API keys so tests never hit the network,
and serves the legacy template views so their tests keep exercising them
(the React SPA is covered through the /api/v1 tests)."""

import os

from django.conf import settings
from django.test.runner import DiscoverRunner


class HermeticTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        for key in ('GEMINI_API_KEY', 'YOUTUBE_API_KEY', 'BREVO_API_KEY'):
            os.environ[key] = ''
            setattr(settings, key, '')
        settings.ALVIX_FRONTEND = 'templates'
        # uploads in tests stay on local disk, never in the Supabase bucket
        from django.core.files.storage import default_storage, storages
        from django.utils.functional import empty
        settings.STORAGES = {**settings.STORAGES,
                             'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}}
        storages._backends = None
        storages._storages = {}
        default_storage._wrapped = empty
        super().setup_test_environment(**kwargs)
