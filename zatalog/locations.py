"""Resolve external catalog sources declared by Location entities."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from zatalog.entity import Entity
from zatalog.errors import CatalogFileError


def resolve_location(entity: Entity) -> list[Path]:
    """Resolve a supported Location entity into local catalog descriptor paths."""
    if entity.kind.lower() != "location":
        return []
    location_type = str(entity.spec.get("type", "")).lower()
    if location_type != "git":
        return []
    target = entity.spec.get("target")
    if not isinstance(target, str) or not target:
        raise CatalogFileError(f"{entity.ref}: git Location requires spec.target")
    revision = str(entity.spec.get("ref") or "HEAD")
    checkout = _checkout(target, revision)
    requested = entity.spec.get("paths", entity.spec.get("path", "catalog-info.yaml"))
    patterns = requested if isinstance(requested, list) else [requested]
    found: list[Path] = []
    for pattern in patterns:
        if not isinstance(pattern, str) or not pattern:
            raise CatalogFileError(
                f"{entity.ref}: Location paths must be non-empty strings"
            )
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise CatalogFileError(
                f"{entity.ref}: Location path must stay inside the repository: {pattern}"
            )
        matches = sorted(checkout.glob(pattern))
        for match in matches:
            if match.is_dir():
                matches_in_dir = [
                    *match.rglob("catalog-info.yaml"),
                    *match.rglob("catalog-info.yml"),
                ]
                found.extend(sorted(matches_in_dir))
            elif match.is_file():
                found.append(match)
    if not found:
        raise CatalogFileError(
            f"{entity.ref}: no catalog files matched {patterns!r} in {target}"
        )
    root = checkout.resolve()
    resolved = list(dict.fromkeys(path.resolve() for path in found))
    escaped = [path for path in resolved if not path.is_relative_to(root)]
    if escaped:
        raise CatalogFileError(
            f"{entity.ref}: Location path escapes the repository: {escaped[0]}"
        )
    return resolved


def _checkout(target: str, revision: str) -> Path:
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    key = hashlib.sha256(f"{target}\0{revision}".encode()).hexdigest()[:20]
    checkout = cache_home / "zatalog" / "git" / key
    checkout.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not (checkout / ".git").is_dir():
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--no-single-branch",
                    target,
                    str(checkout),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        subprocess.run(
            ["git", "-C", str(checkout), "fetch", "--depth", "1", "origin", revision],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(checkout),
                "checkout",
                "--detach",
                "--force",
                "FETCH_HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as e:
        detail = (
            e.stderr.strip()
            if isinstance(e, subprocess.CalledProcessError) and e.stderr
            else str(e)
        )
        raise CatalogFileError(
            f"Cannot load git catalog {target} at {revision}: {detail}"
        ) from e
    return checkout
