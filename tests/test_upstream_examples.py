from pathlib import Path

import yaml

import zatalog.entity
from zatalog.entity import expand_placeholders, load_entities_from_file

FIXTURES = Path(__file__).parent / "fixtures" / "vendor" / "backstage"


def test_backstage_descriptor_format_text_example(monkeypatch) -> None:
    swagger = '{"swagger":"2.0","info":{"title":"Swagger Petstore"}}'
    monkeypatch.setattr(zatalog.entity, "_read_placeholder", lambda target: swagger)

    entity = load_entities_from_file(FIXTURES / "petstore-api.yaml")[0]

    assert entity.metadata.name == "petstore"
    assert entity.spec["definition"] == swagger


def test_backstage_software_template_yaml_examples(monkeypatch) -> None:
    content_by_url = {
        "https://github.com/example/path/to/parameters.yaml": (
            FIXTURES / "parameters.yaml"
        ).read_text(encoding="utf-8"),
        "https://github.com/example/path/to/action.yaml": (
            FIXTURES / "action.yaml"
        ).read_text(encoding="utf-8"),
    }
    monkeypatch.setattr(
        zatalog.entity,
        "_read_placeholder",
        lambda target: content_by_url[str(target)],
    )
    source = FIXTURES / "template-fragment.yaml"
    fragment = yaml.safe_load(source.read_text(encoding="utf-8"))

    expanded = expand_placeholders(fragment, source)

    assert expanded["spec"]["parameters"][0]["title"] == "Provide simple information"
    assert expanded["spec"]["steps"][0] == {
        "id": "publish",
        "name": "Publish files",
        "action": "publish:github",
        "input": {"repoUrl": "${{ parameters.url }}"},
    }
