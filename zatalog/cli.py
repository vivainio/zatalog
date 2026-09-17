"""zatalog CLI - Main entry point."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from typing import Any

import yaml

from zatalog import __version__
from zatalog.catalog import Catalog, load_catalog, resolve_catalog_paths
from zatalog.entity import Entity
from zatalog.errors import ApplicationError
from zatalog.query import (
    available_annotations,
    available_labels,
    get_path,
    jira_info,
    resolve_annotation,
    resolve_label,
)
from zatalog.schema import validate_entity


def _load_catalog(args: argparse.Namespace) -> Catalog:
    paths = resolve_catalog_paths(args.file, args.root, args.recursive)
    return load_catalog(paths)


def _entity_to_dict(entity: Entity) -> dict[str, Any]:
    return {
        "apiVersion": entity.api_version,
        "kind": entity.kind,
        "metadata": {k: v for k, v in asdict(entity.metadata).items() if v not in (None, {}, [])},
        "spec": entity.spec,
        "source": str(entity.source) if entity.source else None,
    }


def _dump(value: Any, fmt: str) -> str:
    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if fmt == "json":
        return json.dumps(value, indent=2, default=str)
    return yaml.safe_dump(value, sort_keys=False, default_flow_style=False)


def list_command(args: argparse.Namespace) -> None:
    catalog = _load_catalog(args)
    entities = catalog.all(kind=args.kind)
    if not entities:
        print("No entities found.")
        return
    for entity in entities:
        title = f" ({entity.metadata.title})" if entity.metadata.title else ""
        print(f"{entity.ref}{title}")


def show_command(args: argparse.Namespace) -> None:
    catalog = _load_catalog(args)
    entity = catalog.get(args.ref)
    print(_dump(_entity_to_dict(entity), args.format).rstrip())


def get_command(args: argparse.Namespace) -> None:
    catalog = _load_catalog(args)
    entity = catalog.get(args.ref)
    try:
        value = get_path(entity, args.field)
    except KeyError as e:
        raise ApplicationError(str(e)) from e
    print(_dump(value, args.format).rstrip() if isinstance(value, (dict, list)) else value)


def _not_found_error(kind: str, key: str, entity: Entity, available: list[tuple[str, str, Entity]], walk: bool) -> ApplicationError:
    scope = f"{entity.ref}" + (" or its System/Domain" if walk else "")
    if available:
        hint = f"; {entity.ref} chain has: {', '.join(k for k, _, _ in available)}"
    else:
        hint = "; none set anywhere in the chain"
    return ApplicationError(f"{kind} '{key}' not set on {scope}{hint}")


def _print_entries(entries: list[tuple[str, str, Entity]], entity: Entity) -> None:
    for key, value, source in entries:
        suffix = f"  # inherited from {source.ref}" if source.ref != entity.ref else ""
        print(f"{key}: {value}{suffix}")


def annotation_command(args: argparse.Namespace) -> None:
    catalog = _load_catalog(args)
    entity = catalog.get(args.ref)
    walk = not args.no_walk
    value, source = resolve_annotation(catalog, entity, args.key, walk=walk)
    if value is None:
        raise _not_found_error("Annotation", args.key, entity, available_annotations(catalog, entity, walk=walk), walk)
    if source.ref != entity.ref:
        print(f"{value}  # inherited from {source.ref}", file=sys.stderr)
    print(value)


def annotations_command(args: argparse.Namespace) -> None:
    catalog = _load_catalog(args)
    entity = catalog.get(args.ref)
    entries = available_annotations(catalog, entity, walk=not args.no_walk)
    if not entries:
        print(f"No annotations set on {entity.ref}" + ("" if args.no_walk else " or its System/Domain"))
        return
    _print_entries(entries, entity)


def label_command(args: argparse.Namespace) -> None:
    catalog = _load_catalog(args)
    entity = catalog.get(args.ref)
    walk = not args.no_walk
    value, source = resolve_label(catalog, entity, args.key, walk=walk)
    if value is None:
        raise _not_found_error("Label", args.key, entity, available_labels(catalog, entity, walk=walk), walk)
    if source.ref != entity.ref:
        print(f"{value}  # inherited from {source.ref}", file=sys.stderr)
    print(value)


def labels_command(args: argparse.Namespace) -> None:
    catalog = _load_catalog(args)
    entity = catalog.get(args.ref)
    entries = available_labels(catalog, entity, walk=not args.no_walk)
    if not entries:
        print(f"No labels set on {entity.ref}" + ("" if args.no_walk else " or its System/Domain"))
        return
    _print_entries(entries, entity)


def jira_command(args: argparse.Namespace) -> None:
    catalog = _load_catalog(args)
    entity = catalog.get(args.ref)
    info = jira_info(catalog, entity, project_annotation=args.annotation, walk=not args.no_walk)
    if info is None:
        raise ApplicationError(
            f"No '{args.annotation}' annotation found on {entity.ref}"
            + ("" if args.no_walk else " or its System/Domain")
        )
    if args.format == "json":
        print(
            json.dumps(
                {
                    "projects": [{"key": p.key, "instance": p.instance} for p in info.projects],
                    "component": info.component,
                    "label": info.label,
                    "source": str(info.source.ref),
                },
                indent=2,
            )
        )
        return
    for project in info.projects:
        print(str(project))
    if info.component:
        print(f"component: {info.component}", file=sys.stderr)
    if info.label:
        print(f"label: {info.label}", file=sys.stderr)
    if info.source.ref != entity.ref:
        print(f"(resolved via {info.source.ref})", file=sys.stderr)


def refs_command(args: argparse.Namespace) -> None:
    catalog = _load_catalog(args)
    entity = catalog.get(args.ref)
    relations = catalog.relations(entity)
    if not relations:
        print(f"{entity.ref} declares no relations.")
        return
    for relation in relations:
        status = "" if relation.resolved else "  [dangling]"
        print(f"{relation.name} -> {relation.ref}{status}")


def validate_command(args: argparse.Namespace) -> None:
    catalog = _load_catalog(args)
    entities = catalog.all()
    problems: list[str] = []
    for entity in entities:
        for problem in validate_entity(entity):
            problems.append(f"{entity.ref}: schema {problem}")
        for relation in catalog.relations(entity):
            if not relation.resolved:
                problems.append(f"{entity.ref}: {relation.name} -> {relation.ref} does not resolve")
    if not problems:
        print(f"OK: {len(entities)} entities, schemas valid and all relations resolve.")
        return
    for problem in problems:
        print(problem)
    raise ApplicationError(f"{len(problems)} problem(s) found across {len(entities)} entities")


def _add_catalog_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-f",
        "--file",
        action="append",
        help="Catalog-info file to load (repeatable). Default: search upward from cwd.",
    )
    parser.add_argument(
        "--root",
        help="Directory to scan for catalog-info files instead of walking up from cwd.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan --root (or cwd) recursively for every catalog-info.y[a]ml file.",
    )


def _add_ref_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "ref",
        help="Entity reference, e.g. 'component:default/my-service' or just 'my-service'",
    )


_MAIN_EPILOG = """\
examples:
  zatalog list                                    # what's loaded
  zatalog show my-service                         # full entity, resolved
  zatalog get my-service spec.owner                # one field
  zatalog annotation my-service jira/project-key   # walks up to System/Domain if unset
  zatalog annotations my-service                   # what annotations are actually set (incl. inherited)
  zatalog refs my-service                          # outgoing relations
  zatalog validate                                 # schema + relation check across the whole catalog

'my-service' resolves to 'component:default/my-service' if the name is
unambiguous; otherwise qualify it, e.g. 'component:default/my-service'.

Run 'zatalog <command> --help' for that command's own examples.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zatalog",
        description="Parse and fully evaluate Backstage catalog-info.yaml files",
        epilog=_MAIN_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    list_parser = subparsers.add_parser("list", help="List loaded entities")
    _add_catalog_args(list_parser)
    list_parser.add_argument("-k", "--kind", help="Filter by kind, e.g. Component")
    list_parser.set_defaults(func=list_command)

    show_parser = subparsers.add_parser("show", help="Show a fully parsed entity")
    _add_catalog_args(show_parser)
    _add_ref_arg(show_parser)
    show_parser.add_argument("--format", choices=["yaml", "json"], default="yaml")
    show_parser.set_defaults(func=show_command)

    get_parser = subparsers.add_parser(
        "get",
        help="Read a dotted field path off an entity (e.g. spec.type)",
        epilog=(
            "examples:\n"
            "  zatalog get my-service spec.type\n"
            "  zatalog get my-service spec.owner\n"
            "  zatalog get my-service metadata.tags.0\n"
            "  zatalog get my-service spec --format json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_catalog_args(get_parser)
    _add_ref_arg(get_parser)
    get_parser.add_argument("field", help="Dotted field path, e.g. 'spec.owner' or 'metadata.tags.0'")
    get_parser.add_argument("--format", choices=["yaml", "json"], default="yaml")
    get_parser.set_defaults(func=get_command)

    annotation_parser = subparsers.add_parser(
        "annotation",
        help="Read an annotation, walking up to System/Domain if unset",
        epilog=(
            "examples:\n"
            "  zatalog annotation my-service backstage.io/managed-by-location\n"
            "  zatalog annotation my-service jira/project-key --no-walk\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_catalog_args(annotation_parser)
    _add_ref_arg(annotation_parser)
    annotation_parser.add_argument("key", help="Annotation key, e.g. 'backstage.io/managed-by-location'")
    annotation_parser.add_argument("--no-walk", action="store_true", help="Only check the entity itself")
    annotation_parser.set_defaults(func=annotation_command)

    annotations_parser = subparsers.add_parser(
        "annotations",
        help="List every annotation visible on an entity, walking up to System/Domain if unset",
        epilog=(
            "examples:\n"
            "  zatalog annotations my-service\n"
            "  zatalog annotations my-service --no-walk\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_catalog_args(annotations_parser)
    _add_ref_arg(annotations_parser)
    annotations_parser.add_argument("--no-walk", action="store_true", help="Only check the entity itself")
    annotations_parser.set_defaults(func=annotations_command)

    label_parser = subparsers.add_parser(
        "label",
        help="Read a label, walking up to System/Domain if unset",
        epilog="examples:\n  zatalog label my-service tier\n  zatalog label my-service tier --no-walk\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_catalog_args(label_parser)
    _add_ref_arg(label_parser)
    label_parser.add_argument("key", help="Label key")
    label_parser.add_argument("--no-walk", action="store_true", help="Only check the entity itself")
    label_parser.set_defaults(func=label_command)

    labels_parser = subparsers.add_parser(
        "labels",
        help="List every label visible on an entity, walking up to System/Domain if unset",
        epilog="examples:\n  zatalog labels my-service\n  zatalog labels my-service --no-walk\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_catalog_args(labels_parser)
    _add_ref_arg(labels_parser)
    labels_parser.add_argument("--no-walk", action="store_true", help="Only check the entity itself")
    labels_parser.set_defaults(func=labels_command)

    jira_parser = subparsers.add_parser(
        "jira",
        help="Resolve the Jira project(s) for an entity (jira/project-key annotation)",
        epilog=(
            "examples:\n"
            "  zatalog jira my-service\n"
            "  zatalog jira my-service --format json\n"
            "  zatalog jira my-service --annotation jira/secondary-project-key\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_catalog_args(jira_parser)
    _add_ref_arg(jira_parser)
    jira_parser.add_argument(
        "--annotation",
        default="jira/project-key",
        help="Annotation key to read (default: jira/project-key)",
    )
    jira_parser.add_argument("--no-walk", action="store_true", help="Only check the entity itself")
    jira_parser.add_argument("--format", choices=["text", "json"], default="text")
    jira_parser.set_defaults(func=jira_command)

    refs_parser = subparsers.add_parser("refs", help="Show an entity's outgoing relations")
    _add_catalog_args(refs_parser)
    _add_ref_arg(refs_parser)
    refs_parser.set_defaults(func=refs_command)

    validate_parser = subparsers.add_parser("validate", help="Check that every relation in the catalog resolves")
    _add_catalog_args(validate_parser)
    validate_parser.set_defaults(func=validate_command)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except ApplicationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(e.exit_code)


if __name__ == "__main__":
    main()
