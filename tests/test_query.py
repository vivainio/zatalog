from zatalog.query import get_path, jira_info, resolve_annotation


def test_get_path_spec_field(catalog) -> None:
    entity = catalog.get("component:default/payments-api")
    assert get_path(entity, "spec.type") == "service"
    assert get_path(entity, "metadata.name") == "payments-api"
    assert get_path(entity, "spec.providesApis.0") == "payments-api-spec"


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
