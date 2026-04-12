from __future__ import annotations


class UniversalIIIFError(Exception):
    """Base exception for all Scriptoria custom exceptions."""


class NetworkError(UniversalIIIFError):
    """Network connectivity or request failures."""


class HTTPError(NetworkError):
    """HTTP-specific errors (status codes)."""


class ManifestNotFoundError(HTTPError):
    """Manifest not found (404)."""


class RateLimitError(HTTPError):
    """Rate limit exceeded (429)."""


class RequestTimeoutError(NetworkError):
    """Connection or request timeout."""


class ManifestError(UniversalIIIFError):
    """IIIF manifest-related errors."""


class InvalidManifestError(ManifestError):
    """Manifest is malformed or invalid."""


class ManifestParseError(ManifestError):
    """Error parsing manifest JSON."""


class StorageError(UniversalIIIFError):
    """Storage and database errors."""


class DatabaseError(StorageError):
    """Database operation failures."""


class VaultError(StorageError):
    """Vault-specific operation failures."""


class FileOperationError(UniversalIIIFError):
    """File I/O operation errors."""


class DownloadError(FileOperationError):
    """Download operation failures."""


class ImageProcessingError(FileOperationError):
    """Image processing failures."""


class OCRError(UniversalIIIFError):
    """OCR processing errors."""


class ModelLoadError(OCRError):
    """ML model loading failures."""


class OCRProcessingError(OCRError):
    """OCR processing operation failures."""


class JobError(UniversalIIIFError):
    """Job management errors."""


class AsyncError(JobError):
    """Async operation failures."""


class ThreadingError(JobError):
    """Threading operation failures."""


class ResolverError(UniversalIIIFError):
    """Exception raised when a resolver cannot normalize or resolve an identifier.

    Raise this with a user-friendly message that can be surfaced to the UI.
    """

    def __init__(self, message: str) -> None:  # noqa: D107
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:  # pragma: no cover - trivial  # noqa: D105
        return self.message
