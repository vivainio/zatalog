import sys
from pathlib import Path
from typing import Any

import pytest

from zatalog.cli import build_parser
from zatalog.errors import ApplicationError

FIXTURE = str(Path(__file__).parent / "fixtures" / "catalog-info.yaml")


def run(capsys, command, *rest) -> Any:
    parser = build_parser()
    args = parser.parse_args([command, "-f", FIXTURE, *rest])
    args.func(args)
    return capsys.readouterr()


def test_list(capsys) -> None:
    out = run(capsys, "list").out
    assert "Component:default/payments-api" in out
    assert "System:default/payments-system" in out


def test_list_filtered_by_kind(capsys) -> None:
    out = run(capsys, "list", "--kind", "Component").out
    assert "payments-api" in out
    assert "System:default/payments-system" not in out


def test_show(capsys) -> None:
    out = run(capsys, "show", "component:default/payments-api").out
    assert "kind: Component" in out
    assert "type: service" in out


def test_show_discovers_catalog_in_parent_directory(
    capsys, monkeypatch, tmp_path
) -> None:
    project = tmp_path / "project"
    nested = project / "src" / "package"
    nested.mkdir(parents=True)
    (project / "catalog-info.yaml").write_text(
        Path(FIXTURE).read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.chdir(nested)
    parser = build_parser()
    args = parser.parse_args(["show", "component:default/payments-api"])

    args.func(args)

    out = capsys.readouterr().out
    assert "name: payments-api" in out
    assert "type: service" in out


def test_get(capsys) -> None:
    out = run(capsys, "get", "component:default/payments-api", "spec.type").out
    assert out.strip() == "service"


def test_jira_direct(capsys) -> None:
    out = run(capsys, "jira", "component:default/checkout-service").out
    assert "CHK" in out
    assert "secondary/OTH" in out


def test_jira_inherited(capsys) -> None:
    result = run(capsys, "jira", "component:default/payments-api")
    assert "PAY" in result.out
    assert "resolved via Domain:default/payments-domain" in result.err


def test_jira_missing_raises() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["jira", "-f", FIXTURE, "api:default/payments-api-spec", "--no-walk"]
    )
    with pytest.raises(ApplicationError):
        args.func(args)


def test_annotations_lists_direct_and_inherited(capsys) -> None:
    out = run(capsys, "annotations", "component:default/payments-api").out
    assert (
        "jira/project-key: PAY  # inherited from Domain:default/payments-domain" in out
    )


def test_annotations_no_walk_hides_inherited(capsys) -> None:
    out = run(capsys, "annotations", "component:default/payments-api", "--no-walk").out
    assert "No annotations set on Component:default/payments-api" in out


def test_annotation_missing_hints_available_keys() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "annotation",
            "-f",
            FIXTURE,
            "component:default/checkout-service",
            "no/such-key",
        ]
    )
    with pytest.raises(
        ApplicationError, match="chain has: jira/component, jira/project-key"
    ):
        args.func(args)


def test_labels_empty_when_none_set(capsys) -> None:
    out = run(capsys, "labels", "component:default/checkout-service").out
    assert (
        "No labels set on Component:default/checkout-service or its System/Domain"
        in out
    )


def test_validate_without_jsonschema_hints_extra(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    monkeypatch.delitem(sys.modules, "zatalog.schema", raising=False)
    parser = build_parser()
    args = parser.parse_args(["validate", "-f", FIXTURE])
    with pytest.raises(ApplicationError, match=r"pip install 'zatalog\[cli\]'"):
        args.func(args)


def test_validate_reports_dangling(capsys) -> None:
    parser = build_parser()
    args = parser.parse_args(["validate", "-f", FIXTURE])
    with pytest.raises(ApplicationError):
        args.func(args)
    out = capsys.readouterr().out
    assert "schema spec: 'definition' is a required property" in out
    assert "nonexistent-service" in out


def test_validate_accepts_valid_catalog(capsys, tmp_path) -> None:
    catalog_file = tmp_path / "catalog-info.yaml"
    catalog_file.write_text(
        """
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: valid-service
spec:
  type: service
  lifecycle: production
  owner: group:default/owners
---
apiVersion: backstage.io/v1alpha1
kind: Group
metadata:
  name: owners
spec:
  type: team
  children: []
""",
        encoding="utf-8",
    )
    parser = build_parser()
    args = parser.parse_args(["validate", "-f", str(catalog_file)])

    args.func(args)

    assert "schemas valid and all relations resolve" in capsys.readouterr().out
