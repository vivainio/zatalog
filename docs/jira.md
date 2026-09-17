# Jira metadata

Store Jira information as annotations under `metadata.annotations`:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: checkout-api
  annotations:
    jira/project-key: PAY
    jira/component: Checkout API
    jira/label: checkout
spec:
  type: service
  lifecycle: production
  owner: group:default/payments
```

The supported annotations are:

| Annotation | Meaning |
|---|---|
| `jira/project-key` | One or more Jira projects |
| `jira/component` | Jira Component field value |
| `jira/label` | Jira label applied to the entity |

Query the resolved Jira data:

```console
$ zatalog jira checkout-api
PAY
component: Checkout API
label: checkout
```

Component and label details are written to stderr, which keeps stdout useful
for scripts that only need project keys. Use JSON to get one structured result:

```console
$ zatalog jira checkout-api --format json
{
  "projects": [
    {
      "key": "PAY",
      "instance": null
    }
  ],
  "component": "Checkout API",
  "label": "checkout",
  "source": "Component:default/checkout-api"
}
```

## Multiple projects and Jira instances

Separate projects with commas. Prefix a project with an instance name when it
belongs to a non-default Jira site:

```yaml
metadata:
  annotations:
    jira/project-key: "PAY, cloud/PLATFORM"
```

```console
$ zatalog jira checkout-api
PAY
cloud/PLATFORM
```

In JSON output, `cloud/PLATFORM` becomes project key `PLATFORM` with instance
`cloud`.

## Define Jira data once on a System or Domain

For a large application, keep shared Jira data on its System:

```yaml
apiVersion: backstage.io/v1alpha1
kind: System
metadata:
  name: storefront
  annotations:
    jira/project-key: STORE
    jira/component: Storefront
spec:
  owner: group:default/commerce
  domain: commerce
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: checkout-api
spec:
  type: service
  lifecycle: production
  owner: group:default/payments
  system: storefront
```

`zatalog jira checkout-api` finds the annotations through `spec.system`. A
Domain can provide a broader default through `System.spec.domain`.

Resolution order is Component → System → Domain. Each annotation resolves
independently, so the project can come from a Domain while the Jira Component
field comes from a System. A value declared directly on the Component wins.

Use `--no-walk` when inherited values should be ignored:

```bash
zatalog jira checkout-api --no-walk
```

## Read individual annotations

The generic annotation command works for Jira and organization-specific data:

```bash
zatalog annotation checkout-api jira/project-key
zatalog annotation checkout-api jira/component
zatalog annotation checkout-api jira/label
```

It uses the same inheritance walk unless `--no-walk` is present.

## Use a different project annotation

If an organization already uses another annotation name, select it without
changing the descriptor:

```yaml
metadata:
  annotations:
    example.com/jira-project: PAY
```

```bash
zatalog jira checkout-api --annotation example.com/jira-project
```

The `jira/component` and `jira/label` annotations continue to resolve normally.
