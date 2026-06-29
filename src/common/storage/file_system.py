"""Local filesystem storage backend with a signed-URL compatibility shim.

Provides :class:`FileSystemStorageAccessToken` — a thin wrapper around
Django's built-in :class:`~django.core.files.storage.FileSystemStorage` that
adds a ``generate_upload_signed_url_v4`` method so that local-dev code can
call the same interface used by the production GCS backend without error.
"""

from typing import Any

from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class FileSystemStorageAccessToken(FileSystemStorage):
    """Local filesystem storage with a GCS-compatible signed-URL interface.

    Extends :class:`~django.core.files.storage.FileSystemStorage` to expose
    a ``generate_upload_signed_url_v4`` method that returns a plain file-system
    URL rather than a real signed URL.  This lets development code share the
    same upload interface as the production :class:`~common.storage.google.GoogleCloudStorageAccessToken`
    backend.
    """

    def generate_upload_signed_url_v4(
        self,
        name: str,
        _method: str = "PUT",
        **_kwargs: Any,
    ) -> dict[str, str]:
        """Return a local-filesystem URL in the same shape as the GCS signed-URL response.

        Args:
            name: Storage path / object name for the resource.
            _method: Intended HTTP method (ignored in the local implementation).
            **_kwargs: Additional keyword arguments (ignored).

        Returns:
            Dict with keys ``"url"`` (full URL), ``"base_url"`` (base path),
            and ``"relative_url"`` (object name).
        """
        return {
            "url": self.url(name=name),
            "base_url": self.base_url,
            "relative_url": name,
        }
