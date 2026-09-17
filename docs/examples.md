# Examples

For Jira-specific examples, including multiple projects and inheritance, see
[Jira metadata](jira.md).

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

## Central Systems and Domains repository

Keep organization-wide entities in a separate repository and import them from
each application catalog:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Location
metadata:
  name: organization-catalog
spec:
  type: git
  target: https://github.com/example/organization-catalog.git
  ref: main
  paths: [systems/*.yaml, domains/*.yaml]
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

If the imported `storefront` System points to a Domain, normal inheritance can
continue from the local Component through both remote entities.

## Share a Splunk index across an application

Put operational metadata on the System when every Component in the application
uses the same Splunk index:

```yaml
apiVersion: backstage.io/v1alpha1
kind: System
metadata:
  name: storefront
  annotations:
    splunk/index: storefront-production
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

Resolve it from the Component:

```console
$ zatalog annotation checkout-api splunk/index
storefront-production
# inherited from System:default/storefront
```

Use a Component annotation when one service writes to a different index; its
local value overrides the System. Put the annotation on a Domain only when the
same index truly spans several Systems. Annotation values are strings, so an
organization that needs several indexes can define its own convention, such as
a comma-separated `splunk/indexes` value.
