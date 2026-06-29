"""Google Cloud Storage backend with access-token-based signed-URL support.

Provides :class:`GoogleCloudStorageAccessToken` — an extended
:class:`~storages.backends.gcloud.GoogleCloudStorage` backend that:

* Generates public or signed URLs depending on bucket ACL and
  ``querystring_auth`` settings.
* Caches short-lived GCP access-token credentials to minimise calls to the
  Google metadata server.
* Adds ``generate_upload_signed_url_v4`` for creating v4 signed upload URLs.
* Exposes ``get_file_path`` / ``get_file_name`` helpers for path generation.
"""

import datetime
import uuid
from pathlib import Path
from typing import Any

import google.auth
import google.auth.transport.requests
from django.core.cache import cache
from django.utils.deconstruct import deconstructible
from google.cloud.storage.blob import _quote
from google.oauth2 import service_account
from storages.backends.gcloud import GoogleCloudStorage
from storages.utils import clean_name


@deconstructible
class GoogleCloudStorageAccessToken(GoogleCloudStorage):
    """Google Cloud Storage backend with access-token caching and v4 signed URLs.

    Extends :class:`~storages.backends.gcloud.GoogleCloudStorage` to add:

    * Token caching via Django cache so credentials are refreshed only when
      they expire.
    * A ``generate_upload_signed_url_v4`` method used by upload endpoints.
    * Static helpers ``get_file_path`` and ``get_file_name``.

    Attributes:
        CACHE_KEY: Django cache key used to store signing credentials.
        default_acl: Default ACL applied to new blobs.
        querystring_auth: Whether signed query-string authentication is used.
        custom_endpoint: Optional custom storage endpoint URL.
        expiration: Default signed-URL TTL in seconds (7 days).
    """

    CACHE_KEY = "GoogleCloudStorageAccessToken.signing_extras"
    default_acl = getattr(GoogleCloudStorage, "default_acl", None)
    querystring_auth = getattr(GoogleCloudStorage, "querystring_auth", True)
    custom_endpoint = getattr(GoogleCloudStorage, "custom_endpoint", None)
    expiration = getattr(GoogleCloudStorage, "expiration", 604800)

    def url(self, name: str, **_kwargs: Any) -> str:
        """Return a public or signed URL for the named blob.

        Chooses between a plain public URL, a custom-endpoint URL, and a
        v4 signed URL based on the ``default_acl``, ``querystring_auth``,
        and ``custom_endpoint`` settings.

        Args:
            name: Object name / storage path.
            **_kwargs: Additional keyword arguments (forwarded to signed-URL
                generation when applicable).

        Returns:
            URL string for accessing the blob.
        """
        name = self._normalize_name(clean_name(name))
        blob = self.bucket.blob(name)
        no_signed_url = self.default_acl == "publicRead" or not self.querystring_auth
        if not self.custom_endpoint and no_signed_url:
            return str(blob.public_url)
        if no_signed_url:
            return str(
                "{storage_base_url}/{quoted_name}".format(
                    storage_base_url=self.custom_endpoint,
                    quoted_name=_quote(name, safe=b"/~"),
                )
            )
        expiration = datetime.timedelta(seconds=self.expiration)
        if not self.custom_endpoint:
            return str(
                blob.generate_signed_url(
                    expiration, version="v4", **self.signed_url_extra()
                )
            )
        return str(
            blob.generate_signed_url(
                expiration=expiration,
                version="v4",
                api_access_endpoint=self.custom_endpoint,
                **self.signed_url_extra(),
            )
        )

    def signed_url_extra(self) -> dict[str, Any]:
        """Return the signing kwargs passed to ``blob.generate_signed_url``.

        For a service-account key (local private key) returns just
        ``{"credentials": ...}`` and signs locally. For keyless
        (workload-identity) environments, mints and caches a short-lived
        access token and returns ``"service_account_email"`` /
        ``"access_token"`` / ``"credentials"`` for IAM SignBlob signing.
        """
        value = cache.get(self.CACHE_KEY)
        if value is not None:
            expiry, extra = value
            if expiry > datetime.datetime.now(datetime.UTC):
                return dict(extra)

        credentials, _project_id = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

        # A mounted service-account key can sign URLs locally with its private
        # key — no IAM SignBlob round-trip and no access-token refresh (the
        # bare credentials carry no OAuth scope, so a refresh raises
        # invalid_scope). The token path below is only for keyless
        # (workload-identity) environments.
        if isinstance(credentials, service_account.Credentials):
            return {"credentials": credentials}

        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        extra = {
            "service_account_email": credentials.service_account_email,
            "access_token": credentials.token,
            "credentials": credentials,
        }

        cache.set(self.CACHE_KEY, (credentials.expiry, extra))
        return extra

    @staticmethod
    def get_file_path(path: str, _: Any, filename: str) -> str:
        """Generate a storage path that replaces the original filename with a UUID.

        Preserves the file extension from the original filename so the stored
        object retains the correct content type hint.

        Args:
            path: Target directory path inside the storage bucket.
            _: Unused placeholder (e.g. Django model instance).
            filename: Original uploaded filename including extension.

        Returns:
            Full storage path as a string (``"<path>/<uuid>.<ext>"``).
        """
        ext = filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        return str(Path(path) / filename)

    def generate_upload_signed_url_v4(
        self,
        name: str,
        _method: str = "PUT",
        **_kwargs: Any,
    ) -> dict[str, str]:
        """Generate a GCS v4 signed URL that permits a direct file upload.

        Args:
            name: Object name / storage path for the upload target.
            _method: HTTP method the signed URL will permit (default ``"PUT"``).
            **_kwargs: Additional parameters merged into the signed-URL request;
                override default ``expiration``, ``version``, or ``method``.

        Returns:
            Dict with keys ``"url"`` (full signed URL), ``"base_url"``
            (bucket base URL), and ``"relative_url"`` (object name).
        """
        name = self._normalize_name(clean_name(name))
        blob = self.bucket.blob(name)
        default_params = {
            "expiration": self.expiration,
            "version": "v4",
            "method": _method,
        }

        params = _kwargs or {}
        for key, value in default_params.items():
            if value and key not in params:
                params[key] = value
        return {
            "url": blob.generate_signed_url(**params),
            "base_url": f"https://storage.googleapis.com/{self.bucket.name}/",
            "relative_url": name,
        }

    @staticmethod
    def get_file_name(file_field: Any) -> str:
        """Extract the base filename from a Django ``FieldFile`` or similar object.

        Args:
            file_field: A Django ``FieldFile`` or any object with a ``.name``
                attribute.  Falsy values return an empty string.

        Returns:
            The base filename (no directory components), or ``""`` if the
            input is empty or ``None``.
        """
        if not file_field:
            return ""
        return Path(file_field.name).name
