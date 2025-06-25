class ResourceError(Exception):
    """Base class for all resource-related exceptions."""

    pass


class ObjectStateError(ResourceError):
    """Raised when an instance is in an error state."""

    pass


class ObjectNotFoundError(ResourceError):
    """Raised when an instance is not found."""

    pass


class ResourceMultipleFoundError(ResourceError):
    """Raised when multiple instances are found for a given identifier."""

    pass
