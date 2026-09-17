# Getting started

## Install for development

```bash
git clone https://github.com/vivainio/zatalog.git
cd zatalog
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Create a catalog

Create `catalog-info.yaml` in a project root:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: payment-api
  description: Processes customer payments
  annotations:
    jira/project-key: PAY
    jira/component: Payment API
spec:
  type: service
  lifecycle: production
  owner: group:default/payments
---
apiVersion: backstage.io/v1alpha1
kind: Group
metadata:
  name: payments
spec:
  type: team
  children: []
```

## Query it

```bash
zatalog list
zatalog show payment-api
zatalog get payment-api spec.lifecycle
zatalog jira payment-api
zatalog validate
```

Commands search the current directory and then each parent directory for
`catalog-info.yaml` or `catalog-info.yml`. Run them from anywhere below the
project root. Use `-f` for an explicit file or `--root DIR --recursive` to load
catalogs across a larger tree.
