from zatalog.entity import Entity, entity_from_doc
from zatalog.schema import validate_entity


def component(**spec) -> Entity:
    return entity_from_doc(
        {
            "apiVersion": "backstage.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "example"},
            "spec": spec,
        }
    )


def test_validates_known_core_kind() -> None:
    entity = component(type="service", lifecycle="production", owner="team-a")

    assert validate_entity(entity) == []


def test_reports_field_path_for_invalid_known_kind() -> None:
    entity = component(type="service", lifecycle="production")

    assert validate_entity(entity) == ["spec: 'owner' is a required property"]


def test_validates_metadata_constraints() -> None:
    entity = component(type="service", lifecycle="production", owner="team-a")
    entity.raw["metadata"]["name"] = ""

    problems = validate_entity(entity)

    assert problems
    assert all(problem.startswith("metadata.name:") for problem in problems)


def test_requires_spec_for_known_kind() -> None:
    entity = component(type="service", lifecycle="production", owner="team-a")
    del entity.raw["spec"]

    assert validate_entity(entity) == ["<root>: 'spec' is a required property"]


def test_validates_template() -> None:
    entity = entity_from_doc(
        {
            "apiVersion": "scaffolder.backstage.io/v1beta3",
            "kind": "Template",
            "metadata": {"name": "example-template"},
            "spec": {"type": "service", "owner": "team-a", "parameters": [], "steps": []},
        }
    )

    assert validate_entity(entity) == []


def test_accepts_custom_kind_without_a_bundled_schema() -> None:
    entity = entity_from_doc(
        {
            "apiVersion": "example.com/v1",
            "kind": "Widget",
            "metadata": {"name": "anything"},
            "spec": {"organizationSpecific": True},
        }
    )

    assert validate_entity(entity) == []
