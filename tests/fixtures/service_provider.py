from unittest.mock import Mock

import pytest

from dicontainer.container import ServiceProvider


class MockServiceProvider(ServiceProvider):
    """A mock service provider that returns a mock
    service object for any service type.
    """

    def get_service(self, service_type: type) -> object | None:
        return Mock(spec=service_type)


@pytest.fixture
def service_provider() -> MockServiceProvider:
    """Returns a mock service provider."""
    return MockServiceProvider()
