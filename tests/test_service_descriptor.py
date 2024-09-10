from typing import Any
from unittest.mock import Mock, patch

import pytest

from dicontainer.container import (
    ServiceDescriptor,
    ServiceLifetime,
    ServiceProvider,
    _Factory,  # pyright: ignore [reportPrivateUsage]
)

from .fixtures.service_descriptor import (
    ServiceDescriptorBuilder,
    ServiceFactory,
    str_factory_func,
    str_keyed_factory_func,
)


@pytest.fixture
def builder() -> ServiceDescriptorBuilder:
    return ServiceDescriptorBuilder(str)


class TestConstructor:
    def test_service_type_cannot_be_None(self):
        with pytest.raises(ValueError):
            ServiceDescriptor(None, None)  # pyright: ignore[reportArgumentType]

    def test_implementation_is_provided(self, builder: ServiceDescriptorBuilder):
        with pytest.raises(ValueError, match="Implementation must be provided"):
            builder.build()

    def test_lifetime_is_required_for_not_singleton(
        self, builder: ServiceDescriptorBuilder
    ):
        with pytest.raises(ValueError, match="Lifetime must be specified"):
            builder.with_implementation_type(str).build()

    def test_lifetime_is_singleton_for_instance_by_default(self):
        descriptor = ServiceDescriptor(str, None, instance="test")
        assert descriptor.lifetime == ServiceLifetime.SINGLETON

    def test_lifetime_must_be_singleton_for_instance(
        self, service_factory: ServiceFactory
    ):
        with pytest.raises(ValueError, match="Lifetime must be Singleton"):
            _ = service_factory.transient.with_instance()

    def test_implementation_mutually_exclusive(self, builder: ServiceDescriptorBuilder):
        with pytest.raises(
            ValueError, match="instance and implementation_type/factory"
        ):
            builder.with_instance("test").with_implementation_type(str).build()

        with pytest.raises(
            ValueError, match="instance and implementation_type/factory"
        ):
            builder.with_instance("test").with_factory(lambda _: "test").build()

        with pytest.raises(ValueError, match="implementation_type and factory"):
            (
                builder.with_lifetime(ServiceLifetime.SCOPED)
                .with_implementation_type(str)
                .with_factory(lambda _: "test")
            ).build()

    def test_factory_must_be_callable(self, builder: ServiceDescriptorBuilder):
        with pytest.raises(TypeError, match="is not a callable"):
            builder.with_lifetime(ServiceLifetime.SCOPED).with_factory("test").build()  # pyright: ignore[reportArgumentType]

    def test_not_keyed_service_accepts_factory_with_two_args(
        self,
        service_provider_mock: ServiceProvider,
        builder: ServiceDescriptorBuilder,
    ):
        factory_func = Mock(return_value="test")
        descriptor = (
            builder.with_lifetime(ServiceLifetime.SCOPED)
            .with_factory(factory_func)
            .build()
        )

        assert descriptor.service_key is None, "Service must be not keyed"
        assert descriptor.implementation_factory is not None, "Factory must be set"

        descriptor.implementation_factory(service_provider_mock)
        factory_func.assert_called_once_with(service_provider_mock, kwargs=None)

    @pytest.mark.parametrize(
        "func",
        [
            lambda: "test",
            lambda _, __, ___: "test",  # pyright: ignore[reportUnknownArgumentType, reportUnknownLambdaType]
        ],
    )
    def test_factory_takes_only_one_or_two_args(
        self, func: Any, builder: ServiceDescriptorBuilder
    ):
        with pytest.raises(ValueError, match="Unexpected factory callable"):
            builder.with_lifetime(ServiceLifetime.SCOPED).with_factory(func).build()


def test_implementation_instance(builder: ServiceDescriptorBuilder):
    instance = "test"
    builder = builder.with_lifetime(ServiceLifetime.SINGLETON).with_instance(instance)

    descriptor = builder.build()
    assert descriptor.implementation_instance == instance
    with pytest.raises(RuntimeError, match="This service descriptor is not keyed"):
        _ = descriptor.keyed_implementation_instance

    keyed_descriptor = builder.with_service_key("test").build()
    assert keyed_descriptor.implementation_instance is None
    assert keyed_descriptor.keyed_implementation_instance == instance


def test_implementation_type(builder: ServiceDescriptorBuilder):
    itype = str
    builder = builder.with_lifetime(ServiceLifetime.SINGLETON).with_implementation_type(
        itype
    )

    descriptor = builder.build()
    assert descriptor.implementation_type == itype
    with pytest.raises(RuntimeError, match="This service descriptor is not keyed"):
        _ = descriptor.keyed_implementation_type

    keyed_descriptor = builder.with_service_key("test").build()
    assert keyed_descriptor.implementation_type is None
    assert keyed_descriptor.keyed_implementation_type == itype


def test_implementation_factory(builder: ServiceDescriptorBuilder):
    builder = builder.with_lifetime(ServiceLifetime.SCOPED).with_factory(
        str_keyed_factory_func
    )
    descriptor = builder.build()

    assert descriptor.implementation_factory is not None
    with pytest.raises(RuntimeError, match="This service descriptor is not keyed"):
        _ = descriptor.keyed_implementation_factory

    keyed_descriptor = builder.with_service_key("test").build()
    assert keyed_descriptor.implementation_factory is None
    assert keyed_descriptor.keyed_implementation_factory == str_keyed_factory_func


@pytest.fixture(
    params=[
        ("implementation_instance", "test"),
        ("implementation_type", "test"),
        ("implementation_factory", "test"),
        ("implementation_instance", None),
        ("implementation_type", None),
        ("implementation_factory", None),
    ]
)
def str_data(
    builder: ServiceDescriptorBuilder, request: pytest.FixtureRequest
) -> tuple[ServiceDescriptor, str]:
    builder = builder.with_lifetime(ServiceLifetime.SINGLETON)
    descriptor_str: str = "service_type: str lifetime: SINGLETON "

    impl, service_key = request.param

    if service_key is not None:
        builder = builder.with_service_key("test")
        descriptor_str += f"service_key: {service_key} "

    descriptor_str += impl + ": {}"

    value: str | None = None
    if impl == "implementation_instance":
        builder = builder.with_instance("test")
        value = "test"
    elif impl == "implementation_type":
        builder = builder.with_implementation_type(str)
        value = "str"
    elif impl == "implementation_factory":
        if service_key is not None:
            builder = builder.with_factory(str_keyed_factory_func)
            value = "str_keyed_factory_func(_: dicontainer.container.ServiceProvider, __: object | None) -> str"
        else:
            builder = builder.with_factory(str_factory_func)
            value = "str_factory_func(_: dicontainer.container.ServiceProvider) -> str"

    descriptor = builder.build()
    expected = descriptor_str.format(value)
    return (descriptor, expected)


def test_str(str_data: tuple[ServiceDescriptor, str]):
    descriptor, expected = str_data
    assert str(descriptor) == expected


def test_get_implementation_type_throws_if_not_set():
    descriptor = ServiceDescriptor(str, ServiceLifetime.SINGLETON, instance="test")
    with (
        patch.object(descriptor, "_implementation_instance", None),
        pytest.raises(ValueError, match="must be non null"),
    ):
        _ = descriptor.get_implementation_type()


@pytest.mark.parametrize(
    ("key", "impl", "expected"),
    [
        pytest.param(None, {"instance": "test"}, str, id="not keyed, instance"),
        pytest.param(
            None, {"implementation_type": str}, str, id="not keyed, implementation_type"
        ),
        pytest.param(None, {"factory": str_factory_func}, str, id="not keyed, factory"),
        pytest.param(
            None,
            {"factory": str_keyed_factory_func},
            str,
            id="not keyed, keyed factory",
        ),
        pytest.param("test", {"instance": "test"}, str, id="keyed, instance"),
        pytest.param(
            "test", {"implementation_type": str}, str, id="keyed, implementation_type"
        ),
        pytest.param(
            "test", {"factory": str_keyed_factory_func}, str, id="keyed, factory"
        ),
    ],
)
def test_get_implementation_type(key: object, impl: dict[str, Any], expected: type):
    descriptor = ServiceDescriptor(
        str, ServiceLifetime.SINGLETON, service_key=key, **impl
    )
    assert descriptor.get_implementation_type() == expected


@pytest.mark.parametrize(
    ("key", "impl", "expected"),
    [
        pytest.param(None, str, str, id="not keyed, implementation_type"),
        pytest.param(None, str_factory_func, str, id="not keyed, factory"),
        pytest.param(None, str_keyed_factory_func, str, id="not keyed, keyed factory"),
        pytest.param("test", str, str, id="keyed, implementation_type"),
        pytest.param("test", str_keyed_factory_func, str, id="keyed, keyed factory"),
    ],
)
def test_describe(key: object | None, impl: type | _Factory, expected: type):
    descriptor = ServiceDescriptor.describe(
        str, impl, ServiceLifetime.SINGLETON, service_key=key
    )
    assert descriptor.get_implementation_type() == expected


def test_transient():
    descriptor = ServiceDescriptor.transient(str, str_factory_func)
    assert descriptor.lifetime == ServiceLifetime.TRANSIENT

    descriptor = ServiceDescriptor.keyed_transient(
        str, str_keyed_factory_func, service_key="test"
    )
    assert descriptor.lifetime == ServiceLifetime.TRANSIENT


def test_scoped():
    descriptor = ServiceDescriptor.scoped(str, str_factory_func)
    assert descriptor.lifetime == ServiceLifetime.SCOPED

    descriptor = ServiceDescriptor.keyed_scoped(
        str, str_keyed_factory_func, service_key="test"
    )
    assert descriptor.lifetime == ServiceLifetime.SCOPED


@pytest.mark.parametrize(
    "impl",
    [str, str_keyed_factory_func, "test_instance"],
    ids=["type", "factory", "instance"],
)
@pytest.mark.parametrize("service_key", [None, "test"], ids=["not keyed", "keyed"])
def test_singleton(impl: type | _Factory | object, service_key: object | None):
    method_to_mock = "describe" if impl == "test_instance" else "using_instance"
    with patch.object(ServiceDescriptor, method_to_mock) as mock:
        if service_key is not None:
            descriptor = ServiceDescriptor.keyed_singleton(str, impl, "test")
        else:
            descriptor = ServiceDescriptor.singleton(str, impl)
    mock.assert_not_called()
    assert descriptor.lifetime == ServiceLifetime.SINGLETON


class TestKeyedService:
    @pytest.fixture
    def builder(self, builder: ServiceDescriptorBuilder) -> ServiceDescriptorBuilder:
        return builder.with_service_key("test")

    def test_factory_expects_two_args(self, builder: ServiceDescriptorBuilder):
        with pytest.raises(
            ValueError, match="Keyed service factory must take exactly two parameters"
        ):
            builder.with_lifetime(ServiceLifetime.SCOPED).with_factory(
                str_factory_func
            ).build()
