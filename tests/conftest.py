from pathlib import Path

import pytest

from zatalog.catalog import Catalog, load_catalog

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def catalog() -> Catalog:
    return load_catalog([FIXTURES / "catalog-info.yaml"])
