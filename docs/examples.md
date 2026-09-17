# Examples

## One application with several components

Model the application as a System and independently meaningful units as
Components:

```yaml
apiVersion: backstage.io/v1alpha1
kind: System
metadata:
  name: storefront
  annotations:
    jira/project-key: STORE
spec:
  owner: group:default/commerce
  domain: commerce
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: storefront-web
spec:
  type: website
  lifecycle: production
  owner: group:default/web-team
  system: storefront
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: checkout-api
  annotations:
    jira/component: Checkout
spec:
  type: service
  lifecycle: production
  owner: group:default/payments
  system: storefront
```

Both Components inherit Jira project `STORE`. Only `checkout-api` supplies a
more specific Jira component value.

## One monolith

A single Component is enough when the application has one owner, deployment,
lifecycle, and operational identity:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: accounting-monolith
  annotations:
    jira/project-key: ACCT
spec:
  type: service
  lifecycle: production
  owner: group:default/accounting
```

Split it later if parts gain independent ownership, deployment, or operational
responsibility.
