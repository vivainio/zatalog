"""Entity model and parsing for Backstage catalog descriptor documents.

Mirrors the shape defined by Backstage's own JSON schemas
(packages/catalog-model/src/schema/Entity.schema.json and friends in the
backstage/backstage repo): apiVersion + kind + metadata + spec. Since `spec`
differs per kind (and users can register arbitrary custom kinds), it is kept
as a plain dict rather than a per-kind dataclass -- callers reach into it with
`Entity.get_spec()` or the dotted-path helpers in `zatalog.query`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from zatalog.errors import CatalogFileError

DEFAULT_NAMESPACE = "default"

_REF_RE = re.compile(r"^(?:([^:/\s]+):)?(?:([^:/\s]+)/)?([^:/\s]+)$")


class EntityRef(NamedTuple):
    """A parsed `[<kind>:][<namespace>/]<name>` entity reference.

    Comparisons and catalog lookups are case-insensitive (kind, namespace and
    name are all case-folded), matching Backstage's own uniqueness rules --
    but the original casing is preserved for display via `str()`.
    """

    kind: str | None
    namespace: str
    name: str

    @property
    def key(self) -> str:
        """Lowercased `kind:namespace/name` used as the catalog's lookup key."""
        return f"{(self.kind or '').lower()}:{self.namespace.lower()}/{self.name.lower()}"

    def __str__(self) -> str:
        kind = f"{self.kind}:" if self.kind else ""
        return f"{kind}{self.namespace}/{self.name}"


def parse_entity_ref(
    ref: str,
    default_kind: str | None = None,
    default_namespace: str = DEFAULT_NAMESPACE,
) -> EntityRef:
    """Parse a Backstage entity reference string.

    Accepts any of: "component:default/my-service", "default/my-service",
    "my-service", "system:payments".
    """
    match = _REF_RE.match(ref.strip())
    if not match:
        raise ValueError(f"Not a valid entity reference: {ref!r}")
    kind, namespace, name = match.groups()
    return EntityRef(
        kind=kind or default_kind,
        namespace=namespace or default_namespace,
        name=name,
    )


@dataclass
class EntityMetadata:
    """The `metadata` block common to every entity kind."""

    name: str
    namespace: str = DEFAULT_NAMESPACE
    title: str | None = None
    description: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityMetadata:
        return cls(
            name=data["name"],
            namespace=data.get("namespace") or DEFAULT_NAMESPACE,
            title=data.get("title"),
            description=data.get("description"),
            labels=dict(data.get("labels") or {}),
            annotations=dict(data.get("annotations") or {}),
            tags=list(data.get("tags") or []),
            links=list(data.get("links") or []),
        )


@dataclass
class Entity:
    """A fully parsed catalog entity (Component, API, System, Domain, ...)."""

    api_version: str
    kind: str
    metadata: EntityMetadata
    spec: dict[str, Any] = field(default_factory=dict)
    source: Path | None = None

    @property
    def ref(self) -> EntityRef:
        return EntityRef(kind=self.kind, namespace=self.metadata.namespace, name=self.metadata.name)

    def get_spec(self, key: str, default: Any = None) -> Any:
        return self.spec.get(key, default)

    def __str__(self) -> str:
        return str(self.ref)


def parse_documents(text: str) -> list[dict[str, Any]]:
    """Split a catalog-info.yaml file into its raw YAML documents.

    A single file commonly holds several `---`-separated documents (e.g. a
    Location alongside the Component(s) it targets).
    """
    try:
        docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError as e:
        raise CatalogFileError(f"Invalid YAML: {e}") from e
    return [d for d in docs if d]


def entity_from_doc(doc: dict[str, Any], source: Path | None = None) -> Entity:
    """Validate and build an `Entity` from one raw YAML document."""
    where = f" in {source}" if source else ""
    for required in ("apiVersion", "kind", "metadata"):
        if required not in doc:
            raise CatalogFileError(f"Entity missing required field '{required}'{where}")
    metadata = doc["metadata"]
    if not isinstance(metadata, dict) or "name" not in metadata:
        raise CatalogFileError(f"Entity metadata missing required field 'name'{where}")
    return Entity(
        api_version=doc["apiVersion"],
        kind=doc["kind"],
        metadata=EntityMetadata.from_dict(metadata),
        spec=dict(doc.get("spec") or {}),
        source=source,
    )


def load_entities(text: str, source: Path | None = None) -> list[Entity]:
    """Parse every entity document in a catalog-info.yaml file's text."""
    return [entity_from_doc(doc, source) for doc in parse_documents(text)]


def load_entities_from_file(path: Path) -> list[Entity]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise CatalogFileError(f"Cannot read {path}: {e}") from e
    return load_entities(text, source=path)
