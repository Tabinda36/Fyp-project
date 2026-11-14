"""Django storage backend for Supabase Storage.

Every FileField/ImageField upload (profile pictures, course images, lesson PPTs,
assignment files) is stored in one Supabase Storage bucket. Enabled in settings when
SUPABASE_URL, SUPABASE_SECRET_KEY and SUPABASE_STORAGE_BUCKET are set.

Uploaded names get a random token (e.g. profile_pictures/me_3f9c2a1b7d4e.png) so public
URLs cannot be guessed from the original filename.
"""

import mimetypes
import posixpath
import uuid
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class SupabaseStorage(Storage):
    timeout = 60

    def __init__(self, bucket=None, base_url=None, key=None, public=None):
        self.bucket = bucket or settings.SUPABASE_STORAGE_BUCKET
        self.base_url = (base_url or settings.SUPABASE_URL).rstrip('/')
        self.key = key or settings.SUPABASE_SECRET_KEY
        self.public = settings.SUPABASE_STORAGE_PUBLIC if public is None else public
        if not (self.bucket and self.base_url and self.key):
            raise ImproperlyConfigured('SupabaseStorage needs SUPABASE_URL, SUPABASE_SECRET_KEY and SUPABASE_STORAGE_BUCKET.')

    # ------------------------------------------------------------------ helpers
    @property
    def _api(self):
        return f'{self.base_url}/storage/v1'

    def _headers(self, **extra):
        return {'apikey': self.key, 'Authorization': f'Bearer {self.key}', **extra}

    @staticmethod
    def _clean(name):
        return posixpath.normpath(str(name).replace('\\', '/')).lstrip('/')

    def _object_url(self, name):
        return f'{self._api}/object/{self.bucket}/{quote(self._clean(name))}'

    # ---------------------------------------------------------- Storage API
    def get_available_name(self, name, max_length=None):
        name = self._clean(name)
        directory, filename = posixpath.split(name)
        stem, ext = posixpath.splitext(filename)
        token = uuid.uuid4().hex[:12]
        if max_length:
            room = max_length - len(directory) - len(ext) - len(token) - 2
            stem = stem[:max(room, 1)]
        return posixpath.join(directory, f'{stem}_{token}{ext}')

    def _save(self, name, content):
        name = self._clean(name)
        if hasattr(content, 'seek'):
            content.seek(0)
        data = content.read()
        content_type = (getattr(content, 'content_type', None)
                        or getattr(getattr(content, 'file', None), 'content_type', None)
                        or mimetypes.guess_type(name)[0]
                        or 'application/octet-stream')
        resp = requests.post(
            self._object_url(name), data=data, timeout=self.timeout,
            headers=self._headers(**{'Content-Type': content_type, 'x-upsert': 'false',
                                     'cache-control': 'max-age=3600'}),
        )
        if resp.status_code >= 300:
            raise OSError(f'Supabase upload of {name} failed ({resp.status_code}): {resp.text[:300]}')
        return name

    def _open(self, name, mode='rb'):
        resp = requests.get(self._object_url(name), headers=self._headers(), timeout=self.timeout)
        if resp.status_code == 404 or (resp.status_code == 400 and 'not found' in resp.text.lower()):
            raise FileNotFoundError(name)
        if resp.status_code >= 300:
            raise OSError(f'Supabase download of {name} failed ({resp.status_code}): {resp.text[:300]}')
        f = ContentFile(resp.content, name=posixpath.basename(name))
        f.mode = mode
        return f

    def _head(self, name):
        return requests.head(self._object_url(name), headers=self._headers(), timeout=self.timeout)

    def exists(self, name):
        return self._head(name).status_code == 200

    def size(self, name):
        resp = self._head(name)
        if resp.status_code != 200:
            raise FileNotFoundError(name)
        return int(resp.headers.get('content-length') or 0)

    def delete(self, name):
        if not name:
            return
        resp = requests.delete(f'{self._api}/object/{self.bucket}', json={'prefixes': [self._clean(name)]},
                               headers=self._headers(), timeout=self.timeout)
        if resp.status_code >= 300:
            raise OSError(f'Supabase delete of {name} failed ({resp.status_code}): {resp.text[:300]}')

    def url(self, name):
        name = quote(self._clean(name))
        if self.public:
            return f'{self._api}/object/public/{self.bucket}/{name}'
        resp = requests.post(f'{self._api}/object/sign/{self.bucket}/{name}', json={'expiresIn': 3600},
                             headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        return f"{self._api}{resp.json()['signedURL']}"
