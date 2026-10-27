"""Private media storage — files never exposed at a public URL (docs/database.md, EX-6)."""
from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    """Stores under BASE_DIR/private_media/, outside webroot. .url raises to prevent leaks."""

    def __init__(self, **kwargs):
        kwargs.setdefault("location", settings.PRIVATE_MEDIA_ROOT)
        kwargs.setdefault("base_url", None)
        super().__init__(**kwargs)

    def url(self, name):
        raise ValueError("Private media has no public URL. Use an authorized download endpoint.")
