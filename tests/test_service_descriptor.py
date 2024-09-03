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
        builder = self._copy()
        builder._service_type = service_type
        return builder

    def with_instance(self, instance: object) -> Self:
        builder = self._copy()
        builder._instance = instance
        return builder

    def with_factory(self, factory: _Factory) -> Self:
        builder = self._copy()
        builder._factory = factory
        return builder

    def with_implementation_type(self, implementation_type: type) -> Self:
        builder = self._copy()
        builder._implementation_type = implementation_type
        return builder

    def with_lifetime(self, lifetime: ServiceLifetime) -> Self:
        builder = self._copy()
        builder._lifetime = lifetime
        return builder

    def with_service_key(self, service_key: str) -> Self:
        builder = self._copy()
        builder._service_key = service_key
        return builder

    def build(self) -> ServiceDescriptor:
        return ServiceDescriptor(
            self._service_type,
            self._lifetime,
            instance=self._instance,
            factory=self._factory,
            implementation_type=self._implementation_type,
            service_key=self._service_key,
        )

    def _copy(self) -> Self:
        builder = ServiceDescriptorBuilder()
        builder._service_type(self._service_type)
        builder._instance = self._instance
        builder._factory = self._factory
        builder._implementation_type = self._implementation_type
        builder._lifetime = self._lifetime
        builder._service_key = self._service_key
        return builder  # type: ignore

    def __repr__(self) -> str:
        return (
            f"ServiceDescriptorBuilder("
            f"service_type={self._service_type}, "
            f"instance={self._instance}, "
            f"factory={self._factory}, "
            f"implementation_type={self._implementation_type}, "
            f"lifetime={self._lifetime}, "
            f"service_key={self._service_key})"
        )


@fixture
def builder() -> ServiceDescriptorBuilder:
    return ServiceDescriptorBuilder().with_service_type(str)


@fixture
def service_provider():
    return MockServiceProvider()


class TestConstructor:
    def test_service_type_cannot_be_None(self):
        with raises(ValueError):
            ServiceDescriptor(None, None)  # type: ignore

    def test_implementation_is_provided(self, builder: ServiceDescriptorBuilder):
        with raises(ValueError, match="Implementation must be provided"):
            builder.build()

    def test_lifetime_is_required_for_not_singleton(self, builder: ServiceDescriptorBuilder):
        with raises(ValueError, match="Lifetime must be specified"):
            builder.with_implementation_type(str).build()

    def test_lifetime_is_singleton_for_instance_by_default(self):
        descriptor = ServiceDescriptor(str, None, instance="test")
        assert descriptor.lifetime == ServiceLifetime.SINGLETON

    def test_lifetime_must_be_singleton_for_instance(self, builder: ServiceDescriptorBuilder):
        with raises(ValueError, match="Lifetime must be Singleton"):
            builder.with_lifetime(ServiceLifetime.TRANSIENT).with_instance("test").build()

    def test_implementation_mutually_exclusive(self, builder: ServiceDescriptorBuilder):
        with raises(ValueError, match="instance and implementation_type/factory"):
            builder.with_instance("test").with_implementation_type(str).build()

        with raises(ValueError, match="instance and implementation_type/factory"):
            builder.with_instance("test").with_factory(lambda _: "test").build()

        with raises(ValueError, match="implementation_type and factory"):
            (
                builder.with_lifetime(ServiceLifetime.SCOPED)
                .with_implementation_type(str)
                .with_factory(lambda _: "test")
            ).build()

    def test_factory_must_be_callable(self, builder: ServiceDescriptorBuilder):
        with raises(TypeError, match="is not a callable"):
            builder.with_lifetime(ServiceLifetime.SCOPED).with_factory("test").build()  # type: ignore

    def test_not_keyed_service_accepts_factory_with_two_args(
        self,
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
    def test_factory_takes_only_one_or_two_args(self, func: Any, builder: ServiceDescriptorBuilder):
        with raises(ValueError, match="Unexpected factory callable"):
            builder.with_lifetime(ServiceLifetime.SCOPED).with_factory(func).build()


def test_implementation_instance(builder: ServiceDescriptorBuilder):
    instance = "test"
    builder = builder.with_lifetime(ServiceLifetime.SINGLETON).with_instance(instance)

    descriptor = builder.build()
    assert descriptor.implementation_instance == instance
    with raises(RuntimeError, match="This service descriptor is not keyed"):
        _ = descriptor.keyed_implementation_instance

    keyed_descriptor = builder.with_service_key("test").build()
    assert keyed_descriptor.implementation_instance is None
    assert keyed_descriptor.keyed_implementation_instance == instance


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
