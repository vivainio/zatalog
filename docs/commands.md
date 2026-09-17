# Command reference

Catalog input options are shared by all commands: repeatable `-f/--file`,
`--root DIR`, and `--recursive`. Without them, zatalog searches upward.

## `list`

```bash
zatalog list
zatalog list --kind Component
```

## `show`

```bash
zatalog show checkout-api
zatalog show component:default/checkout-api --format json
```

## `get`

Read a dotted field path. Integer segments index lists.

```bash
zatalog get checkout-api spec.lifecycle
zatalog get checkout-api metadata.tags.0
```

## `annotation` and `label`

```bash
zatalog annotation checkout-api jira/project-key
zatalog label checkout-api support-tier
zatalog annotation checkout-api jira/project-key --no-walk
```

By default these commands walk through System and Domain.

## `jira`

```bash
zatalog jira checkout-api
zatalog jira checkout-api --format json
zatalog jira checkout-api --no-walk
```

The project value accepts comma-separated keys and optional instance prefixes,
for example `PAY, cloud/PLATFORM`. The result also includes `jira/component`
and `jira/label` when present.

## `refs`

```bash
zatalog refs checkout-api
```

Shows supported outgoing relations and marks unresolved targets as dangling.

## `validate`

```bash
zatalog validate
zatalog validate --root services --recursive
```

Runs zatalog's schema validation and checks supported relations.
