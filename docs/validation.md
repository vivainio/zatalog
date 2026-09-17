# Validation

`zatalog validate` combines two checks:

1. The expanded raw entity is checked against zatalog's bundled JSON Schema.
2. Supported references are resolved against all loaded entities.

```console
$ zatalog validate
Component:default/checkout: schema spec: 'owner' is a required property
Component:default/checkout: dependsOn -> component:default/inventory does not resolve
Error: 2 problem(s) found across 4 entities
```

The bundled schema covers API, Component, Domain, Group, Location, Resource,
System, User, and Template entities for the API versions listed in the source.
It checks the common envelope, metadata, required kind fields, and basic field
types and reference shapes.

Unknown versions and custom or plugin-owned kinds are accepted without schema
validation. Their data remains available to library consumers and commands.

!!! important

    This is zatalog's schema, not a compatibility copy of Backstage's schema.
    Passing zatalog validation does not promise that a Backstage deployment will
    accept an entity, and the reverse is also true.

The schema is shipped inside the Python package, so validation is deterministic
and does not need network access.
