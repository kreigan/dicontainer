"""Contains `ServiceCollection` fixtures."""

from copy import copy

import pytest

from dicontainer.container import (
    ServiceCollection,
    ServiceDescriptor,
)
from tests.fixtures.service_descriptor import ServiceFactory


@pytest.fixture
def empty_collection() -> ServiceCollection:
    """A `ServiceCollection` fixture with no service added."""
    return ServiceCollection()


class ServiceCollectionFactory:
    """Factory class for creating `ServiceCollection` instances."""

    def __init__(
        self,
        collection: ServiceCollection,
        service_factory: ServiceFactory,
        keyed_service_factory: ServiceFactory,
    ) -> None:
        """Initializes a new instance of the `ServiceCollectionFactory` class.

        Args:
            collection (ServiceCollection): The collection to use for creating new instances.
            service_factory (ServiceFactory): The factory to use for creating new services.
            keyed_service_factory (ServiceFactory): The factory to use for creating new keyed services.
        """
        self._collection = collection
        self.service_factory = service_factory
        self.keyed_service_factory = keyed_service_factory

    def get_collection(self) -> ServiceCollection:
        """Returns a copy of the current collection."""
        return copy(self._collection)

    def singleton_instance(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new singleton service to the collection copy and returns it."""
        return self._add(service or self.service_factory.singleton.instance())

    def transient_instance(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new transient service to the collection copy and returns it."""
        return self._add(service or self.service_factory.transient.instance())

    def scoped_instance(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new scoped service to the collection copy and returns it."""
        return self._add(service or self.service_factory.scoped.instance())

    def singleton_type(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new singleton service to the collection copy and returns it."""
        return self._add(service or self.service_factory.singleton.i_type())

    def transient_type(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new transient service to the collection copy and returns it."""
        return self._add(service or self.service_factory.transient.i_type())

    def scoped_type(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new scoped service to the collection copy and returns it."""
        return self._add(service or self.service_factory.scoped.i_type())

    def singleton_factory(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new singleton service to the collection copy and returns it."""
        return self._add(service or self.service_factory.singleton.factory())

    def transient_factory(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new transient service to the collection copy and returns it."""
        return self._add(service or self.service_factory.transient.factory())

    def scoped_factory(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new scoped service to the collection copy and returns it."""
        return self._add(service or self.service_factory.scoped.factory())

    def singleton_keyed_instance(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new singleton keyed service to the collection copy and returns it."""
        return self._add(service or self.keyed_service_factory.singleton.instance())

    def transient_keyed_instance(
        self, service: ServiceDescriptor | None = None
    ) -> ServiceCollection:
        """Adds a new transient keyed service to the collection copy and returns it."""
        return self._add(service or self.keyed_service_factory.transient.instance())

    def _add(self, service: ServiceDescriptor) -> ServiceCollection:
        collection = self.get_collection()
        collection.append(service)
        return collection


@pytest.fixture
def collection_factory(
    empty_collection: ServiceCollection,
    service_factory: ServiceFactory,
    keyed_service_factory: ServiceFactory,
) -> ServiceCollectionFactory:
    """Factory fixture for creating `ServiceCollectionFactory` instances."""
    return ServiceCollectionFactory(
        empty_collection, service_factory, keyed_service_factory
    )
