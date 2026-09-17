"""Locating catalog-info files on disk."""

from __future__ import annotations

from pathlib import Path

CATALOG_FILENAMES = ("catalog-info.yaml", "catalog-info.yml")


def find_default_catalog_file(start: Path | None = None) -> Path | None:
    """Search upward from `start` (default: cwd) for a catalog-info file.

    Mirrors the "walk up to find the project marker" pattern used for
    zproject.toml in zaira, but for Backstage's own descriptor filename.
    """
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        for name in CATALOG_FILENAMES:
            candidate = parent / name
            if candidate.exists():
                return candidate
    return None


def discover_catalog_files(root: Path, recursive: bool = False) -> list[Path]:
    """Find catalog-info file(s) under `root`.

    Non-recursive: just `root` itself if it directly names a file, or a
    catalog-info file directly inside it if it's a directory.
    Recursive: every catalog-info file anywhere under `root` (a typical
    Backstage monorepo layout has one per package/service).
    """
    if root.is_file():
        return [root]
    if recursive:
        found: list[Path] = []
        for name in CATALOG_FILENAMES:
            found.extend(root.rglob(name))
        return sorted(set(found))
    for name in CATALOG_FILENAMES:
        candidate = root / name
        if candidate.exists():
            return [candidate]
    return []
