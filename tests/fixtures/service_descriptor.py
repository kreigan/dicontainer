"""Contains `ServiceDescriptor` fixtures."""

from typing_extensions import Self

from dicontainer.container import (
    ServiceDescriptor,
    ServiceLifetime,
    ServiceProvider,
    _Factory,  # pyright: ignore [reportPrivateUsage]
)


class ServiceDescriptorBuilder:
    """Builder class for creating `ServiceDescriptor` objects."""

    def __init__(
        self,
        service_type: type,
        instance: object | None = None,
        factory: _Factory | None = None,
        implementation_type: type | None = None,
        lifetime: ServiceLifetime | None = None,
        service_key: str | None = None,
    ) -> None:
        """Initializes a new instance of the `ServiceDescriptorBuilder` class
        for `str` service type.
        """
        self._service_type = service_type
        self._instance = instance
        self._factory = factory
        self._implementation_type = implementation_type
        self._lifetime = lifetime
        self._service_key = service_key

    def with_service_type(self, service_type: type) -> Self:
        builder = self._copy()
        builder._service_type = service_type
        return builder

    @property
    def service_type(self) -> type:
        return self._service_type

    def with_instance(self, instance: object) -> Self:
        builder = self._copy()
        builder._instance = instance
        return builder

    @property
    def instance(self) -> object | None:
        return self._instance

    def with_factory(self, factory: _Factory) -> Self:
        builder = self._copy()
        builder._factory = factory
        return builder

    @property
    def factory(self) -> _Factory | None:
        return self._factory

    def with_implementation_type(self, implementation_type: type) -> Self:
        builder = self._copy()
        builder._implementation_type = implementation_type
        return builder

    @property
    def implementation_type(self) -> type | None:
        return self._implementation_type

    def with_lifetime(self, lifetime: ServiceLifetime) -> Self:
        builder = self._copy()
        builder._lifetime = lifetime
        return builder

    @property
    def lifetime(self) -> ServiceLifetime | None:
        return self._lifetime

    def with_service_key(self, service_key: str) -> Self:
        builder = self._copy()
        builder._service_key = service_key
        return builder

    @property
    def service_key(self) -> str | None:
        return self._service_key

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
        return ServiceDescriptorBuilder(
            self._service_type,
            instance=self._instance,
            factory=self._factory,
            implementation_type=self._implementation_type,
            lifetime=self._lifetime,
            service_key=self._service_key,
        )  # pyright: ignore[reportReturnType]

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


def str_factory_func(_: ServiceProvider) -> str:
    return "test"


def str_keyed_factory_func(_: ServiceProvider, __: object | None) -> str:
    return "test"
