# zatalog

A Python CLI and library for parsing Backstage `catalog-info.yaml` files and
evaluating them locally: expanding descriptor placeholders, resolving entity
references, following the Component/API/Resource → System → Domain hierarchy,
and answering questions
like "what Jira project does this actually belong to?" even when that's only
declared several levels up the hierarchy.

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
  these fields; it does not reimplement full JSON-Schema validation.
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

```
pip install -e .
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

Backstage descriptor substitutions are evaluated before entities are parsed.
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
zatalog validate                           # do supported declared relations resolve?
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

## Development

```
uv sync                    # or: pip install -e . pytest ruff
pytest
ruff check zatalog tests
```
