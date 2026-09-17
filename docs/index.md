# Zatalog

Zatalog gives local tools a shared software catalog built from
`catalog-info.yaml`. It loads entities, expands referenced data, resolves
relationships, and answers practical questions about ownership and Jira.

```bash
pip install -e .
zatalog list
zatalog show my-service
zatalog jira my-service
zatalog validate
```

[Get started](getting-started.md){ .md-button .md-button--primary }
[See examples](examples.md){ .md-button }

## Why Zatalog?

- **One familiar file:** describe services, applications, teams, APIs, and
  domains in readable YAML.
- **Local discovery:** commands find the nearest `catalog-info.yaml` by walking
  up from the current directory.
- **Useful relationships:** connect Components to Systems and Domains instead
  of repeating organization-wide metadata.
- **Extensible data:** custom kinds and arbitrary `spec` fields remain
  available to your own tools.
- **Offline validation:** zatalog ships its own schema for supported kinds.

## Compatibility boundary

Backstage compatibility is not a goal. Zatalog borrows the useful entity shape,
kind names, references, and substitution syntax, but owns its schema and
behavior. It is intended for independent tools that want to share the same file
structure without running or reproducing the Backstage catalog backend.
