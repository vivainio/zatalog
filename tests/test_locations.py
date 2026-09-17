import subprocess

from zatalog.catalog import load_catalog
from zatalog.query import jira_info


def test_git_location_loads_system_and_domain(monkeypatch, tmp_path) -> None:
    remote = tmp_path / "central-catalog"
    remote.mkdir()
    (remote / "catalog-info.yaml").write_text(
        """
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
spec:
  owner: group:default/commerce
  domain: commerce
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(remote)], check=True)
    subprocess.run(["git", "-C", str(remote), "add", "catalog-info.yaml"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(remote),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "catalog",
        ],
        check=True,
    )
    local = tmp_path / "catalog-info.yaml"
    local.write_text(
        f"""
apiVersion: backstage.io/v1alpha1
kind: Location
metadata:
  name: central
spec:
  type: git
  target: {remote}
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: checkout
spec:
  type: service
  lifecycle: production
  owner: group:default/commerce
  system: storefront
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    catalog = load_catalog([local])
    component = catalog.get("checkout")
    info = jira_info(catalog, component)

    assert catalog.get("system:default/storefront").metadata.name == "storefront"
    assert info is not None
    assert info.projects[0].key == "COMM"
    assert info.source.ref == catalog.get("domain:default/commerce").ref
