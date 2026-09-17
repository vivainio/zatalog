from zatalog.errors import EntityNotFoundError


def test_get_by_bare_name(catalog) -> None:
    entity = catalog.get("payments-api")
    assert entity.kind == "Component"


def test_get_ambiguous_name_requires_kind(catalog) -> None:
    # 'payments-team' only exists as a Group, so this should resolve fine...
    assert catalog.get("payments-team").kind == "Group"


def test_get_missing_raises(catalog) -> None:
    try:
        catalog.get("component:default/does-not-exist")
        raise AssertionError("expected EntityNotFoundError")
    except EntityNotFoundError:
        pass


def test_system_of_and_domain_of(catalog) -> None:
    component = catalog.get("component:default/payments-api")
    system = catalog.system_of(component)
    assert system is not None
    assert system.metadata.name == "payments-system"

    domain = catalog.domain_of(component)
    assert domain is not None
    assert domain.metadata.name == "payments-domain"


def test_owner_of_resolves_group(catalog) -> None:
    component = catalog.get("component:default/payments-api")
    owner = catalog.owner_of(component)
    assert owner is not None
    assert owner.kind == "Group"
    assert owner.metadata.name == "payments-team"


def test_ancestry_chain(catalog) -> None:
    component = catalog.get("component:default/payments-api")
    chain = [str(e.ref) for e in catalog.ancestry(component)]
    assert chain == [
        "Component:default/payments-api",
        "System:default/payments-system",
        "Domain:default/payments-domain",
    ]


def test_relations_include_dangling(catalog) -> None:
    checkout = catalog.get("component:default/checkout-service")
    relations = catalog.relations(checkout)
    dangling = [r for r in relations if not r.resolved]
    assert len(dangling) == 1
    assert dangling[0].name == "dependsOn"


def test_relations_resolve_owned_by(catalog) -> None:
    checkout = catalog.get("component:default/checkout-service")
    relations = catalog.relations(checkout)
    owned_by = [r for r in relations if r.name == "ownedBy"]
    assert len(owned_by) == 1
    assert owned_by[0].resolved
