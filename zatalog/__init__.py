"""zatalog - parse and fully evaluate Backstage catalog-info.yaml files."""

from zatalog.catalog import Catalog
from zatalog.entity import Entity, EntityMetadata, EntityRef, parse_entity_ref
from zatalog.errors import ApplicationError, EntityNotFoundError

__version__ = "0.1.0"

__all__ = [
    "Catalog",
    "Entity",
    "EntityMetadata",
    "EntityRef",
    "parse_entity_ref",
    "ApplicationError",
    "EntityNotFoundError",
]
