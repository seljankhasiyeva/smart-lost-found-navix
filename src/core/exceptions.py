class ItemNotFound(Exception):
    """Raised when an item ID does not exist in storage."""

class StorageError(Exception):
    """Raised when a database or filesystem operation fails."""

class ProviderError(Exception):
    """Raised when an AI provider call fails (used for failover bonus)."""

class ValidationError(Exception):
    """Raised when input validation fails."""

class ImageValidationError(ValidationError):
    """Raised when image MIME type, size, or format is invalid."""