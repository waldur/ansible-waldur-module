class ResourceError(Exception):
    """Base class for all resource-related exceptions."""

    pass


class ResourceStateError(ResourceError):
    """Raised when an instance is in an error state."""

    pass


class ResourceNotFoundError(ResourceError):
    """Raised when an instance is not found."""

    pass


class ResourceMultipleFoundError(ResourceError):
    """Raised when multiple instances are found for a given identifier."""

    pass
