"""Contains `ServiceCollection` fixtures."""

import pytest

from dicontainer.container import (
    ServiceCollection,
)


@pytest.fixture
def empty_collection() -> ServiceCollection:
    """A `ServiceCollection` fixture with no service added."""
    return ServiceCollection()
