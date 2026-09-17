import pytest

from zatalog.entity import EntityRef, load_entities, parse_entity_ref
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
