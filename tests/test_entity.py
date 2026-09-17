import pytest

from zatalog.entity import (
    EntityRef,
    expand_placeholders,
    load_entities,
    load_entities_from_file,
    parse_entity_ref,
)
from zatalog.errors import CatalogFileError


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("component:default/my-service", EntityRef("component", "default", "my-service")),
        ("default/my-service", EntityRef(None, "default", "my-service")),
        ("my-service", EntityRef(None, "default", "my-service")),
        ("system:payments", EntityRef("system", "default", "payments")),
    ],
)
def test_parse_entity_ref(ref, expected) -> None:
    assert parse_entity_ref(ref) == expected


def test_parse_entity_ref_invalid() -> None:
    with pytest.raises(ValueError):
        parse_entity_ref("a:b:c")


def test_entity_ref_str_roundtrip() -> None:
    ref = parse_entity_ref("Component:Default/My-Service")
    assert str(ref) == "Component:Default/My-Service"
    assert ref.key == "component:default/my-service"


def test_load_entities_multi_document() -> None:
    text = """
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: a
---
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: b
"""
    entities = load_entities(text)
    assert [e.metadata.name for e in entities] == ["a", "b"]


def test_load_entities_rejects_missing_name() -> None:
    text = """
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  title: no name here
"""
    with pytest.raises(CatalogFileError):
        load_entities(text)


def test_load_entities_rejects_invalid_yaml() -> None:
    with pytest.raises(CatalogFileError):
        load_entities("kind: [unclosed")


def test_expands_text_json_and_yaml_placeholders(tmp_path) -> None:
    (tmp_path / "description.txt").write_text("A detailed description\n", encoding="utf-8")
    (tmp_path / "details.json").write_text(
        '{"type": "service", "flags": [true, 3]}', encoding="utf-8"
    )
    (tmp_path / "extra.yaml").write_text("owner: team-a\ntags:\n  - python\n", encoding="utf-8")
    catalog_file = tmp_path / "catalog-info.yaml"
    catalog_file.write_text(
        """
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: expanded
  description:
    $text: ./description.txt
spec:
  details:
    $json: ./details.json
  extra:
    $yaml: ./extra.yaml
""",
        encoding="utf-8",
    )

    entity = load_entities_from_file(catalog_file)[0]

    assert entity.metadata.description == "A detailed description\n"
    assert entity.spec["details"] == {"type": "service", "flags": [True, 3]}
    assert entity.spec["extra"] == {"owner": "team-a", "tags": ["python"]}


@pytest.mark.parametrize(
    "placeholder",
    [
        {"$json": "./missing.json"},
        {"$json": 42},
    ],
)
def test_invalid_placeholder_is_reported(tmp_path, placeholder) -> None:
    (tmp_path / "data.json").write_text("{}", encoding="utf-8")
    with pytest.raises(CatalogFileError):
        expand_placeholders(placeholder, tmp_path / "catalog-info.yaml")


def test_invalid_json_placeholder_is_reported(tmp_path) -> None:
    (tmp_path / "data.json").write_text("{invalid", encoding="utf-8")
    with pytest.raises(CatalogFileError, match="Invalid JSON"):
        expand_placeholders({"$json": "./data.json"}, tmp_path / "catalog-info.yaml")


def test_unknown_and_ambiguous_placeholders_are_left_unchanged(tmp_path) -> None:
    unknown = {"$ref": "#/components/schemas/Pet"}
    ambiguous = {"$json": "./data.json", "description": "schema metadata"}

    assert expand_placeholders(unknown, tmp_path / "catalog-info.yaml") == unknown
    assert expand_placeholders(ambiguous, tmp_path / "catalog-info.yaml") == ambiguous


def test_yaml_placeholder_requires_exactly_one_document(tmp_path) -> None:
    (tmp_path / "data.yaml").write_text("one: 1\n---\ntwo: 2\n", encoding="utf-8")
    with pytest.raises(CatalogFileError, match="exactly one YAML document"):
        expand_placeholders({"$yaml": "./data.yaml"}, tmp_path / "catalog-info.yaml")
