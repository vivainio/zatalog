"""Field lookups and cross-entity "fully evaluated" queries.

The Jira helpers here exist because Backstage itself does not compute a
"current Jira project" anywhere -- it just renders whatever `jira/*`
annotation happens to sit on the entity you're looking at (see the
@roadiehq/backstage-plugin-jira docs). Fully evaluating that in the way an
engineer actually means it -- "what Jira project does this component's work
land in" -- requires walking up from the entity to its System and then that
System's Domain, since teams commonly set the annotation once at the System
or Domain level rather than repeating it on every Component.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zatalog.catalog import Catalog
from zatalog.entity import Entity, EntityMetadata

_FIELD_ALIASES = {"apiVersion": "api_version"}

JIRA_PROJECT_ANNOTATION = "jira/project-key"
JIRA_COMPONENT_ANNOTATION = "jira/component"
JIRA_LABEL_ANNOTATION = "jira/label"


def get_path(entity: Entity, path: str) -> Any:
    """Resolve a dotted path like 'spec.type' or 'metadata.tags.0' against an entity.

    Only plain identifier/integer segments are supported. Annotation and
    label keys often contain '/' or '.' themselves (e.g.
    'backstage.io/managed-by-location'), so those are looked up with
    `resolve_annotation`/`resolve_label` instead of this generic path getter.
    """
    value = entity
    consumed = []
    for part in path.split("."):
        consumed.append(part)
        value = _get_part(value, part, ".".join(consumed))
    return value


def _get_part(value: Any, part: str, so_far: str) -> Any:
    if isinstance(value, Entity):
        attr = _FIELD_ALIASES.get(part, part)
        if attr in ("api_version", "kind", "metadata", "spec", "source"):
            return getattr(value, attr)
        raise KeyError(f"Entity has no field '{part}' (at '{so_far}')")
    if isinstance(value, EntityMetadata):
        if part in (
            "name",
            "namespace",
            "title",
            "description",
            "labels",
            "annotations",
            "tags",
            "links",
        ):
            return getattr(value, part)
        raise KeyError(f"metadata has no field '{part}' (at '{so_far}')")
    if isinstance(value, dict):
        if part in value:
            return value[part]
        raise KeyError(f"No key '{part}' (at '{so_far}')")
    if isinstance(value, list):
        try:
            index = int(part)
        except ValueError as e:
            raise KeyError(f"'{part}' is not a valid list index (at '{so_far}')") from e
        try:
            return value[index]
        except IndexError as e:
            raise KeyError(f"Index {index} out of range (at '{so_far}')") from e
    raise KeyError(f"Cannot look up '{part}' on {type(value).__name__} (at '{so_far}')")


def resolve_annotation(catalog: Catalog, entity: Entity, key: str, walk: bool = True) -> tuple[str | None, Entity]:
    """Find annotation `key`, walking Component/API/Resource -> System -> Domain if not set directly.

    Returns (value, entity_it_was_found_on). If not found anywhere in the
    chain, returns (None, entity) -- the original entity.
    """
    chain = catalog.ancestry(entity) if walk else [entity]
    for candidate in chain:
        if key in candidate.metadata.annotations:
            return candidate.metadata.annotations[key], candidate
    return None, entity


def resolve_label(catalog: Catalog, entity: Entity, key: str, walk: bool = True) -> tuple[str | None, Entity]:
    chain = catalog.ancestry(entity) if walk else [entity]
    for candidate in chain:
        if key in candidate.metadata.labels:
            return candidate.metadata.labels[key], candidate
    return None, entity


@dataclass
class JiraProjectRef:
    key: str
    instance: str | None = None

    def __str__(self) -> str:
        return f"{self.instance}/{self.key}" if self.instance else self.key


@dataclass
class JiraInfo:
    projects: list[JiraProjectRef]
    component: str | None
    label: str | None
    source: Entity
    raw: str


def jira_info(
    catalog: Catalog,
    entity: Entity,
    project_annotation: str = JIRA_PROJECT_ANNOTATION,
    component_annotation: str = JIRA_COMPONENT_ANNOTATION,
    label_annotation: str = JIRA_LABEL_ANNOTATION,
    walk: bool = True,
) -> JiraInfo | None:
    """The Jira project(s) that apply to `entity`, fully evaluated.

    Supports the roadiehq/backstage-plugin-jira conventions: a
    comma-separated list of project keys, and an optional 'instance/KEY'
    form for a non-default Jira site.
    """
    raw, source = resolve_annotation(catalog, entity, project_annotation, walk=walk)
    if raw is None:
        return None
    projects = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "/" in part:
            instance, _, key = part.partition("/")
            projects.append(JiraProjectRef(instance=instance, key=key))
        else:
            projects.append(JiraProjectRef(key=part))
    component, _ = resolve_annotation(catalog, entity, component_annotation, walk=walk)
    label, _ = resolve_annotation(catalog, entity, label_annotation, walk=walk)
    return JiraInfo(projects=projects, component=component, label=label, source=source, raw=raw)
