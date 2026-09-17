import pytest

from zatalog.query import available_annotations, get_path, jira_info, resolve_annotation


def test_get_path_spec_field(catalog) -> None:
    entity = catalog.get("component:default/payments-api")
    assert get_path(entity, "spec.type") == "service"
    assert get_path(entity, "metadata.name") == "payments-api"
    assert get_path(entity, "spec.providesApis.0") == "payments-api-spec"


def test_get_path_bad_entity_field_lists_fields(catalog) -> None:
    entity = catalog.get("component:default/payments-api")
    with pytest.raises(KeyError, match="fields: apiVersion, kind, metadata, spec, source"):
        get_path(entity, "bogus")


def test_get_path_bad_metadata_field_lists_fields(catalog) -> None:
    entity = catalog.get("component:default/payments-api")
    with pytest.raises(KeyError, match="fields: name, namespace, title, description, labels, annotations, tags, links"):
        get_path(entity, "metadata.bogus")


def test_get_path_bad_dict_key_lists_keys(catalog) -> None:
    entity = catalog.get("component:default/payments-api")
    with pytest.raises(KeyError, match="keys: lifecycle, owner, providesApis, system, type"):
        get_path(entity, "spec.bogus")


def test_get_path_out_of_range_index_lists_valid_range(catalog) -> None:
    entity = catalog.get("component:default/payments-api")
    with pytest.raises(KeyError, match="valid indices: 0-0"):
        get_path(entity, "spec.providesApis.5")


def test_resolve_annotation_direct_hit(catalog) -> None:
    checkout = catalog.get("component:default/checkout-service")
    value, source = resolve_annotation(catalog, checkout, "jira/project-key")
    assert value == "CHK, secondary/OTH"
    assert source is checkout


def test_resolve_annotation_walks_up_to_domain(catalog) -> None:
    component = catalog.get("component:default/payments-api")
    value, source = resolve_annotation(catalog, component, "jira/project-key")
    assert value == "PAY"
    assert source.metadata.name == "payments-domain"


def test_resolve_annotation_no_walk(catalog) -> None:
    component = catalog.get("component:default/payments-api")
    value, source = resolve_annotation(catalog, component, "jira/project-key", walk=False)
    assert value is None
    assert source is component


def test_jira_info_direct_multi_project_with_instance(catalog) -> None:
    checkout = catalog.get("component:default/checkout-service")
    info = jira_info(catalog, checkout)
    assert [str(p) for p in info.projects] == ["CHK", "secondary/OTH"]
    assert info.component == "checkout"


def test_jira_info_inherited_from_domain(catalog) -> None:
    component = catalog.get("component:default/payments-api")
    info = jira_info(catalog, component)
    assert [str(p) for p in info.projects] == ["PAY"]
    assert info.source.metadata.name == "payments-domain"


def test_jira_info_none_when_absent(catalog) -> None:
    api = catalog.get("api:default/payments-api-spec")
    info = jira_info(catalog, api, walk=False)
    assert info is None


def test_available_annotations_merges_chain_closest_wins(catalog) -> None:
    checkout = catalog.get("component:default/checkout-service")
    entries = available_annotations(catalog, checkout)
    by_key = {key: (value, source) for key, value, source in entries}
    assert by_key["jira/project-key"] == ("CHK, secondary/OTH", checkout)
    assert by_key["jira/component"] == ("checkout", checkout)


def test_available_annotations_includes_inherited(catalog) -> None:
    component = catalog.get("component:default/payments-api")
    entries = available_annotations(catalog, component)
    keys = [key for key, _, _ in entries]
    assert keys == ["jira/project-key"]
    _, value, source = entries[0]
    assert value == "PAY"
    assert source.metadata.name == "payments-domain"


def test_available_annotations_empty_when_no_walk_and_none_set(catalog) -> None:
    api = catalog.get("api:default/payments-api-spec")
    assert available_annotations(catalog, api, walk=False) == []
