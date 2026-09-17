"""Error types for zatalog."""


class ApplicationError(Exception):
    """Base error for user-facing failures. Caught at the CLI boundary."""

    exit_code = 1


class CatalogFileError(ApplicationError):
    """A catalog-info file could not be found, read, or parsed."""


class EntityNotFoundError(ApplicationError):
    """A referenced entity does not exist in the loaded catalog."""
