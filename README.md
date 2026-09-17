# zatalog

[Documentation](https://vivainio.github.io/zatalog/)

A Python CLI and library for tools that use the familiar `catalog-info.yaml`
file structure: expanding descriptor placeholders, resolving entity references,
following the Component/API/Resource → System → Domain hierarchy, and answering
questions like "what Jira project does this actually belong to?" even when
that's only declared several levels up the hierarchy.

## Compatibility

Backstage compatibility is not a goal. Zatalog uses the same convenient entity
shape and common kind names so independent tools can share `catalog-info.yaml`,
but it does not attempt to reproduce the Backstage catalog backend, ingestion
pipeline, policies, or validation results. Zatalog owns its schema and behavior;
they may intentionally differ from Backstage as the needs of local tooling
evolve.

## Why

Backstage itself doesn't ship a way to ask "what Jira project covers this
component" from the command line -- it just renders whatever `jira/*`
annotation happens to be on the entity you're looking at. In practice teams
set `jira/project-key` once on a `System` or `Domain` rather than repeating
it on every `Component`, so answering that question "fully" means walking
the ownership graph, not just reading one YAML block.

## Prior art

There's no existing Python package that does this. What exists instead:

- **`@backstage/catalog-model`** (TypeScript, in the
  [backstage/backstage](https://github.com/backstage/backstage) monorepo) --
  the canonical entity model and JSON Schemas
  (`packages/catalog-model/src/schema/Entity.schema.json` and
  `kinds/*.schema.json`). zatalog's `Entity`/`EntityMetadata` shapes mirror
  these fields. Zatalog's model starts from the same shape but is independently
  maintained.
- **`plugin-catalog-backend`** (same repo) -- where Backstage actually
  computes bidirectional `relations` (e.g. a Component's `spec.system`
  becomes a `partOf` relation, and the System gets `hasPart` back) at ingest
  time, server-side. `zatalog`'s `Catalog.relations()` recomputes the
  outgoing half of that from raw source YAML, since there's no backend here.
- **Roadie's [catalog validator](https://roadie.io/docs/catalog/validator/)**
  and the `@backstage/catalog-model` schemas it wraps -- a Node/GitHub Action
  tool for schema-checking `catalog-info.yaml` in CI. zatalog's `validate`
  command checks something they don't: that relations declared in `spec`
  (`system`, `owner`, `dependsOn`, ...) actually resolve within the loaded
  catalog.
- **`@roadiehq/backstage-plugin-jira`** -- defines the `jira/project-key`,
  `jira/component`, and `jira/label` annotations this tool reads by default,
  including the comma-separated multi-project and `instance/KEY` forms.
- The `backstage` package on PyPI is an unrelated Ubuntu task runner, not a
  catalog parser.

In short: catalog-info.yaml parsing and relation modeling already exists,
just not in Python, and not with a CLI aimed at answering ownership/ops
questions like "current Jira project" from a shell prompt.

## Install

As a CLI tool:

```
uv tool install 'zatalog[cli]'
```

The `cli` extra pulls in `jsonschema`, needed for `zatalog validate`; every
other command works without it, so plain `uv tool install zatalog` (or
`pip install zatalog`) is enough if you don't need schema validation.

As a library:

```
pip install zatalog
```

## Library usage

```python
from pathlib import Path

from zatalog.catalog import load_catalog
from zatalog.query import jira_info

catalog = load_catalog([Path("catalog-info.yaml")])
entity = catalog.get("component:default/checkout-service")

info = jira_info(catalog, entity)
print([str(p) for p in info.projects])  # e.g. ["CHK", "secondary/OTH"]
```

## CLI usage

By default, commands search upward from the current directory for a
`catalog-info.yaml`/`.yml`, same as most tools look for a project marker
file. Use `-f/--file` (repeatable) to load specific files, or
`--root DIR --recursive` to load every catalog-info file under a directory
tree (a typical Backstage monorepo layout).

Catalogs can compose definitions from Git repositories through `Location`
entities. Git sources are cached locally and join the same catalog, allowing a
local Component to refer to a centrally maintained System or Domain.

Descriptor substitutions modeled after Backstage are evaluated before entities
are parsed.
`$text` embeds a referenced file as a string, while `$json` and
`$yaml` embed parsed data. Targets may be relative to the descriptor or absolute
HTTP(S) URLs.

```yaml
spec:
  definition:
    $text: ./openapi.yaml
  customData:
    $json: https://example.com/component-data.json
```

```
zatalog list [--kind Component]
zatalog show <ref> [--format yaml|json]
zatalog get <ref> <dotted.path>            # e.g. spec.type, metadata.tags.0
zatalog annotation <ref> <key> [--no-walk] # walks System -> Domain if unset
zatalog label <ref> <key> [--no-walk]
zatalog jira <ref> [--annotation KEY] [--no-walk] [--format text|json]
zatalog refs <ref>                         # outgoing relations, flags dangling ones
zatalog validate                           # schemas valid and supported relations resolve?
```

Entity references accept `kind:namespace/name`, `namespace/name`, or a bare
`name` (resolved if unambiguous) -- e.g. `component:default/checkout-service`
or just `checkout-service`.

### Example: "what's the current Jira project?"

```
$ zatalog jira checkout-service
CHK
secondary/OTH

$ zatalog jira payments-api     # no annotation on the Component itself
PAY
(resolved via Domain:default/payments-domain)
```

## Supported kinds

Component, API, Resource, System, Domain, Group, User, Template -- and any
custom kind, since `spec` is kept as a plain dict. Relation inference
(`Catalog.relations()`, `system_of()`, `domain_of()`, `owner_of()`) is
defined per-kind in `zatalog/catalog.py:RELATION_SPECS` and can be extended
for custom kinds.

`zatalog validate` applies zatalog's own bundled schema to API, Component,
Domain, Group, Location, Resource, System, User, and Template entities. Unknown
versions and custom or plugin-owned kinds are accepted without schema
validation; their `spec` remains available as a plain dictionary. Validation
runs after `$text`, `$json`, and `$yaml` expansion and reports both schema
violations and unresolved supported relations.

## Development

```
uv sync --all-extras       # or: pip install -e '.[cli]' pytest ruff
pytest
ruff check zatalog tests
```
