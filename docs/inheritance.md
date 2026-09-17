# Component → System → Domain inheritance

Zatalog can resolve an annotation or label along an entity's hierarchy:

```text
Component ──spec.system──▶ System ──spec.domain──▶ Domain
    1st                       2nd                    3rd
```

The nearest declared value wins. Values are looked up at query time; zatalog
does not copy inherited data into the Component.

```yaml
apiVersion: backstage.io/v1alpha1
kind: Domain
metadata:
  name: commerce
  annotations:
    jira/project-key: COMM
spec:
  owner: group:default/commerce
---
apiVersion: backstage.io/v1alpha1
kind: System
metadata:
  name: storefront
  annotations:
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

For `checkout-api`, the Jira project resolves from the Domain and the Jira
component resolves from the System. Each annotation or label is resolved
independently, so values can come from different levels.

The same walk applies to API and Resource entities that declare `spec.system`.
It does not walk through Group or User ownership. `--no-walk` restricts a query
to the requested entity.
