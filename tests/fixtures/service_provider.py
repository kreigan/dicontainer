from unittest.mock import Mock

import pytest

from dicontainer.container import ServiceProvider


class MockServiceProvider(ServiceProvider):
    """A mock service provider that returns a mock
    service object for any service type.
    """

    def get_service(
        self,
        service_type: type,
        service_key: object | None = None,  # noqa: ARG002
    ) -> object | None:
        return Mock(spec=service_type)


@pytest.fixture
def service_provider_mock() -> MockServiceProvider:
    """Returns a mock service provider."""
    return MockServiceProvider()
