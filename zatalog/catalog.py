"""The loaded catalog: a registry of entities plus relation resolution.

Backstage itself computes bidirectional `relations` server-side (in
plugin-catalog-backend) from the one-directional references authors write in
`spec` (e.g. a Component's `spec.system` becomes a `partOf` relation, and the
System gets the inverse `hasPart` for free). Since zatalog works directly off
the source YAML with no backend, `Catalog.relations()` recomputes the
outgoing half of that graph so references can be followed and validated.
"""

from __future__ import annotations

from pathlib import Path

from zatalog.discovery import discover_catalog_files, find_default_catalog_file
from zatalog.entity import Entity, EntityRef, load_entities_from_file, parse_entity_ref
from zatalog.errors import CatalogFileError, EntityNotFoundError
from zatalog.locations import resolve_location

# kind -> [(spec key, relation name, default kind for bare refs, is a list)]
RELATION_SPECS: dict[str, list[tuple[str, str, str | None, bool]]] = {
    "component": [
        ("owner", "ownedBy", None, False),
        ("system", "partOf", "system", False),
        ("subcomponentOf", "subcomponentOf", "component", False),
        ("providesApis", "providesApi", "api", True),
        ("consumesApis", "consumesApi", "api", True),
        ("dependsOn", "dependsOn", None, True),
    ],
    "api": [
        ("owner", "ownedBy", None, False),
        ("system", "partOf", "system", False),
    ],
    "resource": [
        ("owner", "ownedBy", None, False),
        ("system", "partOf", "system", False),
        ("dependsOn", "dependsOn", None, True),
    ],
    "system": [
        ("owner", "ownedBy", None, False),
        ("domain", "partOf", "domain", False),
    ],
    "domain": [
        ("owner", "ownedBy", None, False),
        ("subdomainOf", "partOf", "domain", False),
    ],
    "group": [
        ("parent", "childOf", "group", False),
        ("children", "parentOf", "group", True),
        ("members", "hasMember", "user", True),
    ],
    "user": [
        ("memberOf", "memberOf", "group", True),
    ],
    "template": [
        ("owner", "ownedBy", None, False),
    ],
}


class Relation:
    """One resolved (or dangling) outgoing relation of an entity."""

    __slots__ = ("name", "ref", "target")

    def __init__(self, name: str, ref: EntityRef, target: Entity | None) -> None:
        self.name = name
        self.ref = ref
        self.target = target

    @property
    def resolved(self) -> bool:
        return self.target is not None

    def __repr__(self) -> str:
        status = "" if self.resolved else " (dangling)"
        return f"{self.name} -> {self.ref}{status}"


class Catalog:
    """An in-memory registry of entities loaded from one or more files."""

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}

    def add(self, entity: Entity) -> None:
        self._entities[entity.ref.key] = entity

    def add_all(self, entities: list[Entity]) -> None:
        for entity in entities:
            self.add(entity)

    def all(self, kind: str | None = None) -> list[Entity]:
        entities = list(self._entities.values())
        if kind:
            entities = [e for e in entities if e.kind.lower() == kind.lower()]
        return sorted(entities, key=lambda e: (e.kind.lower(), e.metadata.namespace.lower(), e.metadata.name.lower()))

    def try_get(self, ref: str | EntityRef, default_kind: str | None = None) -> Entity | None:
        parsed = ref if isinstance(ref, EntityRef) else parse_entity_ref(ref, default_kind=default_kind)
        if parsed.kind:
            return self._entities.get(parsed.key)
        matches = [
            e
            for e in self._entities.values()
            if e.metadata.namespace.lower() == parsed.namespace.lower()
            and e.metadata.name.lower() == parsed.name.lower()
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    def get(self, ref: str | EntityRef, default_kind: str | None = None) -> Entity:
        parsed = ref if isinstance(ref, EntityRef) else parse_entity_ref(ref, default_kind=default_kind)
        entity = self.try_get(parsed)
        if entity is not None:
            return entity
        if not parsed.kind:
            matches = [
                e
                for e in self._entities.values()
                if e.metadata.namespace.lower() == parsed.namespace.lower()
                and e.metadata.name.lower() == parsed.name.lower()
            ]
            if len(matches) > 1:
                kinds = ", ".join(sorted(m.kind for m in matches))
                raise EntityNotFoundError(
                    f"Ambiguous reference '{ref}' matches multiple kinds ({kinds}); "
                    f"qualify it, e.g. 'component:{parsed}'"
                )
        raise EntityNotFoundError(f"No such entity: '{ref}' (loaded {len(self._entities)} entities)")

    def relations(self, entity: Entity) -> list[Relation]:
        """Outgoing relations declared in `entity.spec`, resolved against this catalog."""
        specs = RELATION_SPECS.get(entity.kind.lower(), [])
        out: list[Relation] = []
        for spec_key, relation_name, default_kind, is_list in specs:
            value = entity.spec.get(spec_key)
            if not value:
                continue
            raw_refs = value if is_list else [value]
            for raw in raw_refs:
                ref = parse_entity_ref(str(raw), default_kind=default_kind, default_namespace=entity.metadata.namespace)
                target = self.try_get(ref)
                out.append(Relation(relation_name, ref, target))
        return out

    def system_of(self, entity: Entity) -> Entity | None:
        ref = entity.spec.get("system")
        if not ref:
            return None
        return self.try_get(parse_entity_ref(str(ref), default_kind="system", default_namespace=entity.metadata.namespace))

    def domain_of(self, entity: Entity) -> Entity | None:
        """The Domain an entity belongs to, via its System if it isn't one itself."""
        if entity.kind.lower() == "domain":
            return None
        if entity.kind.lower() == "system":
            system = entity
        else:
            system = self.system_of(entity)
            if system is None:
                return None
        domain_ref = system.spec.get("domain")
        if not domain_ref:
            return None
        return self.try_get(parse_entity_ref(str(domain_ref), default_kind="domain", default_namespace=system.metadata.namespace))

    def owner_of(self, entity: Entity) -> Entity | None:
        owner_ref = entity.spec.get("owner")
        if not owner_ref:
            return None
        ref = parse_entity_ref(str(owner_ref), default_namespace=entity.metadata.namespace)
        if ref.kind:
            return self.try_get(ref)
        return self.try_get(EntityRef(kind="group", namespace=ref.namespace, name=ref.name)) or self.try_get(
            EntityRef(kind="user", namespace=ref.namespace, name=ref.name)
        )

    def ancestry(self, entity: Entity) -> list[Entity]:
        """[entity, its System (if any), that System's Domain (if any)] -- the
        chain that `zatalog.query.resolve_annotation` walks when looking for
        an annotation that isn't set directly on `entity`.
        """
        chain = [entity]
        system = self.system_of(entity) if entity.kind.lower() != "system" else None
        if system:
            chain.append(system)
        domain = self.domain_of(entity)
        if domain:
            chain.append(domain)
        return chain


def load_catalog(paths: list[Path]) -> Catalog:
    catalog = Catalog()
    pending = [path.resolve() for path in paths]
    loaded: set[Path] = set()
    while pending:
        path = pending.pop(0)
        if path in loaded:
            continue
        loaded.add(path)
        entities = load_entities_from_file(path)
        catalog.add_all(entities)
        for entity in entities:
            pending.extend(candidate for candidate in resolve_location(entity) if candidate not in loaded)
    return catalog


def resolve_catalog_paths(
    files: list[str] | None,
    root: str | None,
    recursive: bool,
) -> list[Path]:
    """Turn CLI file/root/recursive options into a concrete list of paths to load."""
    if files:
        paths = [Path(f) for f in files]
        missing = [p for p in paths if not p.exists()]
        if missing:
            raise CatalogFileError(f"File(s) not found: {', '.join(str(p) for p in missing)}")
        return paths

    root_path = Path(root) if root else Path.cwd()
    if recursive or root:
        found = discover_catalog_files(root_path, recursive=recursive)
        if not found:
            raise CatalogFileError(f"No catalog-info.yaml found under {root_path}")
        return found

    default = find_default_catalog_file()
    if not default:
        raise CatalogFileError(
            "No catalog-info.yaml found in the current directory or any parent. "
            "Pass -f/--file explicitly, or --root/--recursive to scan a directory."
        )
    return [default]
