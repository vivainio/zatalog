# Descriptor files

One YAML file may contain multiple entities separated by `---`. Zatalog also
loads several explicit files with repeated `-f`, or every catalog under a tree
with `--root DIR --recursive`.

## Annotations and labels

Annotations hold tool-specific values:

```yaml
metadata:
  annotations:
    github.com/project-slug: example/payment-api
    jira/project-key: "PAY, cloud/PLATFORM"
    jira/component: Payment API
    jira/label: payments
```

Labels are shorter key/value classifications. Both annotations and labels can
be queried directly and inherited through System and Domain.

## Substitutions

Substitutions are expanded before parsing and validation:

```yaml
spec:
  definition:
    $text: ./openapi.yaml
  configuration:
    $json: ./component.json
  policy:
    $yaml: https://example.com/policy.yaml
```

- `$text` embeds the referenced content as a string.
- `$json` parses and embeds JSON.
- `$yaml` parses and embeds exactly one YAML document.

Targets can be local paths relative to the descriptor or absolute HTTP(S)
URLs. An object containing an unknown dollar-prefixed key such as `$ref`, or a
placeholder alongside sibling keys, is left unchanged.
