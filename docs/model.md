# Catalog model

Every entity has the same envelope:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: checkout-api
spec:
  type: service
```

`apiVersion` and `kind` identify the entity shape. `metadata.name` identifies
the entity within its kind and namespace. `metadata` also carries descriptions,
labels, annotations, tags, and links. `spec` contains kind-specific data and is
kept as a plain dictionary so tools can add their own fields.

## References

The full reference form is:

```text
kind:namespace/name
```

Examples:

```text
component:default/checkout-api
system:commerce/storefront
group:default/payments
```

Within a catalog you can often omit the default namespace and an implied kind:

```yaml
spec:
  owner: payments
  system: storefront
```

Lookups are case-insensitive. A bare name works when it identifies exactly one
loaded entity; qualify ambiguous names with their kind.

## Components, Systems, and Domains

A Component is an independently meaningful unit such as a service, frontend,
worker, library, or monolith. A System groups Components that together form an
application or product. A Domain groups related Systems into a business or
technical area.

```text
Domain: commerce
└── System: storefront
    ├── Component: web-frontend
    ├── Component: checkout-api
    └── Component: order-worker
```

Repository boundaries do not dictate Components. One repository may describe
several Components, and a Component may draw from several repositories.
