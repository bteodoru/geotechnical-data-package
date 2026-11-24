from pathlib import Path

import pytest

from util import unpack

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def pkg_a(tmp_path):
    return unpack(EXAMPLES / "proiect_A.gdp", tmp_path / "A")


@pytest.fixture
def pkg_b(tmp_path):
    return unpack(EXAMPLES / "proiect_B.gdp", tmp_path / "B")
