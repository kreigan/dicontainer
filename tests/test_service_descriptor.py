from typing import Any
from unittest.mock import Mock

from pytest import (
    fixture,
    mark,
    raises,
)
from typing_extensions import Self

from dicontainer.container import (
    ServiceDescriptor,
    ServiceLifetime,
    ServiceProvider,
    _Factory,  # type: ignore
)


class MockServiceProvider(ServiceProvider):
    def get_service(self, service_type: type) -> object | None:
        return Mock(spec=service_type)


class ServiceDescriptorBuilder:
    def __init__(self):
        self._service_type = str
        self._instance = None
        self._factory = None
        self._implementation_type = None
        self._lifetime = None
        self._service_key = None

    def with_service_type(self, service_type: type) -> Self:
        self._service_type = service_type
        return self

    def with_instance(self, instance: object) -> Self:
        self._instance = instance
        return self

    def with_factory(self, factory: _Factory) -> Self:
        self._factory = factory
        return self

    def with_implementation_type(self, implementation_type: type) -> Self:
        self._implementation_type = implementation_type
        return self

    def with_lifetime(self, lifetime: ServiceLifetime) -> Self:
        self._lifetime = lifetime
        return self

    def with_service_key(self, service_key: str) -> Self:
        self._service_key = service_key
        return self

    def build(self) -> ServiceDescriptor:
        return ServiceDescriptor(
            self._service_type,
            self._lifetime,
            instance=self._instance,
            factory=self._factory,
            implementation_type=self._implementation_type,
            service_key=self._service_key,
        )


@fixture
def builder() -> ServiceDescriptorBuilder:
    return ServiceDescriptorBuilder().with_service_type(str)


@fixture
def service_provider():
    return MockServiceProvider()


def test_service_type_cannot_be_None():
    with raises(ValueError):
        ServiceDescriptor(None, None)  # type: ignore


def test_implementation_is_provided(builder: ServiceDescriptorBuilder):
    with raises(ValueError, match="Implementation must be provided"):
        builder.build()


def test_lifetime_is_required_for_not_singleton(builder: ServiceDescriptorBuilder):
    with raises(ValueError, match="Lifetime must be specified"):
        builder.with_implementation_type(str).build()


def test_lifetime_is_singleton_for_instance_by_default():
    descriptor = ServiceDescriptor(str, None, instance="test")
    assert descriptor.lifetime == ServiceLifetime.SINGLETON


def test_lifetime_must_be_singleton_for_instance(builder: ServiceDescriptorBuilder):
    with raises(ValueError, match="Lifetime must be Singleton"):
        builder.with_lifetime(ServiceLifetime.TRANSIENT).with_instance("test").build()


def test_implementation_mutually_exclusive(builder: ServiceDescriptorBuilder):
    with raises(ValueError, match="instance and implementation_type/factory"):
        builder.with_instance("test").with_implementation_type(str).build()

    with raises(ValueError, match="instance and implementation_type/factory"):
        builder.with_instance("test").with_factory(lambda _: "test").build()

    with raises(ValueError, match="implementation_type and factory"):
        # TODO: dirty
        builder = ServiceDescriptorBuilder().with_service_type(str)
        builder.with_lifetime(ServiceLifetime.SCOPED).with_implementation_type(str).with_factory(
            lambda _: "test"
        ).build()


def test_factory_must_be_callable(builder: ServiceDescriptorBuilder):
    with raises(TypeError, match="is not a callable"):
        builder.with_lifetime(ServiceLifetime.SCOPED).with_factory("test").build()  # type: ignore


def test_not_keyed_service_accepts_factory_with_two_args(
    service_provider: ServiceProvider,
    builder: ServiceDescriptorBuilder,
):
    factory_func = Mock(return_value="test")
    descriptor = builder.with_lifetime(ServiceLifetime.SCOPED).with_factory(factory_func).build()

    assert descriptor.service_key is None, "Service must be not keyed"
    assert descriptor.implementation_factory is not None, "Factory must be set"

    descriptor.implementation_factory(service_provider)
    factory_func.assert_called_once_with(service_provider, None)


@mark.parametrize(
    "func",
    [
        lambda: "test",
        lambda _, __, ___: "test",  # type: ignore
    ],
)
def test_factory_takes_only_one_or_two_args(func: Any, builder: ServiceDescriptorBuilder):
    with raises(ValueError, match="Unexpected factory callable"):
        builder.with_lifetime(ServiceLifetime.SCOPED).with_factory(func).build()


def test_implementation_instance_is_set(builder: ServiceDescriptorBuilder):
    descriptor = builder.with_lifetime(ServiceLifetime.SINGLETON).with_instance("test").build()
    assert descriptor.implementation_instance == "test"


class TestKeyedService:
    @fixture
    def keyed_builder(self, builder: ServiceDescriptorBuilder) -> ServiceDescriptorBuilder:
        return builder.with_service_key("test")

    def test_factory_expects_two_args(self, keyed_builder: ServiceDescriptorBuilder):
        with raises(ValueError, match="Keyed service factory must take exactly two parameters"):
            keyed_builder.with_lifetime(ServiceLifetime.SCOPED).with_factory(lambda _: "test").build()

    def test_implementation_instance_is_none(self, keyed_builder: ServiceDescriptorBuilder):
        instance = "test"
        descriptor = keyed_builder.with_lifetime(ServiceLifetime.SINGLETON).with_instance(instance).build()
        assert descriptor.implementation_instance is None
        assert descriptor.keyed_implementation_instance == instance
