"""Offline JSON Schema validation for Backstage's built-in entity kinds."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from typing import Any

import yaml
from jsonschema import Draft7Validator

from zatalog.entity import Entity

_SUPPORTED_ENTITIES = {
    ("backstage.io/v1alpha1", kind)
    for kind in (
        "api",
        "component",
        "domain",
        "group",
        "location",
        "resource",
        "system",
        "user",
    )
} | {
    ("backstage.io/v1beta1", "api"),
    ("backstage.io/v1beta2", "template"),
    ("scaffolder.backstage.io/v1beta3", "template"),
}


@lru_cache(maxsize=1)
def _validator() -> Draft7Validator:
    resource = files("zatalog").joinpath("schemas", "catalog-entity.schema.yaml")
    schema = yaml.safe_load(resource.read_text(encoding="utf-8"))
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema)


def validate_entity(entity: Entity) -> list[str]:
    """Return field-level schema errors for a known kind; custom kinds are accepted."""
    if (entity.api_version, entity.kind.lower()) not in _SUPPORTED_ENTITIES:
        return []
    errors = sorted(
        _validator().iter_errors(entity.raw),
        key=lambda error: list(error.absolute_path),
    )
    return [f"{_format_path(error.absolute_path)}: {error.message}" for error in errors]


def _format_path(parts: Any) -> str:
    path = ""
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += ("." if path else "") + str(part)
    return path or "<root>"
