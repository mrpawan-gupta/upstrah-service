"""Storage helpers and backend re-exports for the VMS project.

Provides two convenience functions for generating unique storage paths and
filenames, and re-exports the concrete storage backend classes used as Django
``DEFAULT_FILE_STORAGE`` / ``STATICFILES_STORAGE`` backends.
"""

import uuid
from typing import Any

from common.storage.file_system import FileSystemStorageAccessToken
from common.storage.google import GoogleCloudStorageAccessToken


def get_file_path(
    base_path: str, instance: Any, filename: str, field: str = "id"
) -> str:
    """Generate a unique storage path based on the model instance and filename.

    Constructs a path of the form
    ``<base_path>/<model_name>/<field_value>/<uuid>.<ext>`` to guarantee
    that no two uploads collide even for the same model instance.

    Args:
        base_path: Root directory path within the storage backend.
        instance: Django model instance whose class name and ``field`` attribute
            are used to build the directory structure.
        filename: Original uploaded filename (used only to extract the extension).
        field: Instance attribute name to use as the sub-directory component.
            Defaults to ``"id"``.

    Returns:
        Full storage path string suitable for use in a ``FileField.upload_to``
        callable.
    """
    ext = filename.split(".")[-1]
    identifier = getattr(instance, field, "default")
    model = instance.__class__.__name__.lower()
    return f"{base_path}/{model}/{identifier}/{uuid.uuid4()}.{ext}"


def get_file_name(extension: str) -> str:
    """Generate a unique filename for the given file extension.

    Strips any leading dot from *extension* and prepends a UUID4 hex string to
    guarantee uniqueness across all uploads.

    Args:
        extension: File extension to append (e.g. ``"pdf"`` or ``".xlsx"``).

    Returns:
        A unique filename string in the form ``"<uuid_hex>.<extension>"``.
    """
    ext = extension.lstrip(".")
    return f"{uuid.uuid4().hex}.{ext}"


__all__ = [
    "FileSystemStorageAccessToken",
    "GoogleCloudStorageAccessToken",
    "get_file_name",
    "get_file_path",
]
