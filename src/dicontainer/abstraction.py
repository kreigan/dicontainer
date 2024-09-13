import inspect
import sys

from abc import abstractmethod
from collections.abc import Callable, Iterable, Iterator
from enum import Enum
from functools import partial
from typing import Protocol, TypeVar, cast, overload

from typing_extensions import Self

from .util import Ensure, class_fqdn


class ServiceLifetime(Enum):
    """Specifies the lifetime of a service in a `ServiceCollection`."""

    SINGLETON = 0
    """Specifies that a single instance of the service will be created."""

    SCOPED = 1
    """Specifies that a new instance of the service will be created for each scope."""

    TRANSIENT = 2
    """Specifies that a new instance of the service will be created every time it is requested."""


_TService_co = TypeVar("_TService_co", bound=object, covariant=True)


class ServiceProviderProto(Protocol):
    """Defines a mechanism for retrieving a service object."""

    @abstractmethod
    def get_service(
        self, service_type: type, service_key: object | None = None
    ) -> object | None:
        """Gets the service object of the specified type.

        Args:
            service_type (type): An object that specifies the type of service object to get.
            service_key (object): An object that specifies the key of the service object to get.

        Returns:
            object: A service object, or `None` if there is no service object of type `service_type`.
        """
        raise NotImplementedError

    def get_service_typed(
        self, service_type: type[_TService_co], service_key: object | None = None
    ) -> _TService_co | None:
        """Get service of type `_TService_co` from the service provider.

        Args:
            service_type (type): The type of service object to get.
            service_key (object): An object that specifies the key of the service object to get.

        Returns:
            object: A service object of type `_TService_co` or `None` if there is no such service.
        """
        return cast(_TService_co, self.get_service(service_type, service_key))

    def get_required_service(
        self, service_type: type, service_key: object | None = None
    ) -> object:
        """Gets service of type `service_type` from the service provider.

        Args:
            service_type (type): An object that specifies the type of service object to get.
            service_key (object): An object that specifies the key of the service object to get.

        Returns:
            object: A service object of type `service_type`.

        Raises:
            RuntimeError: Raised when there is no service object of type `service_type`.
        """
        Ensure.not_none(service_type)

        service = self.get_service(service_type, service_key)
        if service is None:
            raise RuntimeError(
                f"No service for type '{class_fqdn(service_type)}' has been registered."
            )
        return service

    def get_required_service_typed(
        self, service_type: type[_TService_co], service_key: object | None = None
    ) -> _TService_co:
        """Gets service of type `service_type` from the service provider.

        Args:
            service_type (type): An object that specifies the type of service object to get.
            service_key (object): An object that specifies the key of the service object to get.

        Returns:
            object: A service object of type `service_type`.

        Raises:
            RuntimeError: Raised when there is no service object of type `service_type`.
        """
        return cast(_TService_co, self.get_required_service(service_type, service_key))


_ImplementationFactory = Callable[[ServiceProviderProto], object]
_KeyedImplementationFactory = Callable[[ServiceProviderProto, object | None], object]
_Factory = _ImplementationFactory | _KeyedImplementationFactory


class ServiceDescriptor:
    """Describes a service with its service type, implementation, and lifetime."""

    def __init__(
        self,
        service_type: type,
        lifetime: ServiceLifetime | None = None,
        *,
        instance: object | None = None,
        implementation_type: type | None = None,
        factory: _Factory | None = None,
        service_key: object | None = None,
    ) -> None:
        """Initializes a new instance of `ServiceDescriptor` with the specified `implementationType`.

        Args:
            service_type (type): The type of the service.
            lifetime (ServiceLifetime): The lifetime of the service.
            instance (object): The instance implementing the service.
            implementation_type (type): The type implementing the service.
            factory (Callable): A factory used for creating service instances.
            service_key (object): The key used to identify the service.

        Raises:
            ValueError: Raised when `service_type` is `None`.
            ValueError: Raised when `instance` is specified and `lifetime` is not `ServiceLifetime.SINGLETON`.
            ValueError: Raised when `lifetime` is not specified and `instance` is not specified.
            ValueError: Raised when both `instance` and `implementation_type` or `factory` are specified.
            ValueError: Raised when both `implementation_type` and `factory` are specified.
        """

        Ensure.not_none(service_type)

        if not instance and not implementation_type and not factory:
            raise ValueError("Implementation must be provided")

        if not lifetime:
            if not instance:
                raise ValueError(
                    "Lifetime must be specified when not using an instance"
                )
            else:
                lifetime = ServiceLifetime.SINGLETON

        if instance and lifetime != ServiceLifetime.SINGLETON:
            raise ValueError("Lifetime must be Singleton when using an instance")

        if instance and (implementation_type or factory):
            raise ValueError(
                "Cannot specify both instance and implementation_type/factory"
            )

        if implementation_type and factory:
            raise ValueError("Cannot specify both implementation_type and factory")

        keyed_factory = None
        if factory:
            signature = inspect.signature(factory)
            params = signature.parameters
            # Keyed service but one arg function is passed
            if len(params) == 1 and service_key:
                raise ValueError(
                    "Keyed service factory must take exactly two parameters."
                )
            elif len(params) == 2 and not service_key:
                param_name = list(params.values())[1].name
                # If the key is null, use the same factory signature as non-keyed descriptor
                keyed_factory = partial(factory, **{param_name: None})
            elif len(params) not in (1, 2):
                raise ValueError(f"Unexpected factory callable: {signature}")

        self._service_type = service_type
        self._lifetime = lifetime

        self._implementation_instance = instance
        self._implementation_type = implementation_type
        self._implementation_factory = keyed_factory or factory
        self._service_key = service_key

    @property
    def service_type(self) -> type:
        """Gets the type of the service."""
        return self._service_type

    @property
    def lifetime(self) -> ServiceLifetime:
        """Gets the lifetime of the service."""
        return self._lifetime

    @property
    def implementation_instance(self) -> object | None:
        """Gets the instance that implements the service, or returns `None` if
        `is_keyed_service` is `True`.

        If `is_keyed_service` is `True`, `.keyed_implementation_instance()`
        should be called instead.
        """
        if self.is_keyed_service:
            return None
        return self._implementation_instance

    @property
    def keyed_implementation_instance(self) -> object | None:
        """Gets the instance that implements the service, or throws
        `RuntimeError` if `is_keyed_service` is `False`.

        If `is_keyed_service` is `False`, `.implementation_instance()`
        should be called instead.
        """
        if not self.is_keyed_service:
            self._raise_not_keyed_error()
        return self._implementation_instance

    @property
    def implementation_type(self) -> type | None:
        """Gets the type that implements the service, or returns `None` if
        `is_keyed_service` is `True`.

        If `is_keyed_service` is `True`, `.keyed_implementation_type()`
        should be called instead.
        """
        if self.is_keyed_service:
            return None
        return self._implementation_type

    @property
    def keyed_implementation_type(self) -> type | None:
        """Gets the type that implements the service, or throws
        `RuntimeError` if `is_keyed_service` is `False`.

        If `is_keyed_service` is `False`, `.implementation_type()`
        should be called instead.
        """
        if not self.is_keyed_service:
            self._raise_not_keyed_error()
        return self._implementation_type

    @property
    def implementation_factory(self) -> _ImplementationFactory | None:
        """Gets the factory used for creating service instance, or returns `None` if
        `is_keyed_service` is `True`.

        If `is_keyed_service` is `True`, `.keyed_implementation_factory()`
        should be called instead.
        """
        if self.is_keyed_service:
            return None
        return cast(_ImplementationFactory, self._implementation_factory)

    @property
    def keyed_implementation_factory(self) -> _KeyedImplementationFactory | None:
        """Gets the factory used for creating service instance, or throws
        `RuntimeError` if `is_keyed_service` is `False`.

        If `is_keyed_service` is `False`, `.implementation_factory()`
        should be called instead.
        """
        if not self.is_keyed_service:
            self._raise_not_keyed_error()
        return cast(_KeyedImplementationFactory, self._implementation_factory)

    @property
    def service_key(self) -> object | None:
        """Get the key of the service, if applicable."""
        return self._service_key

    @property
    def is_keyed_service(self) -> bool:
        """Indicates whether the service is a keyed service."""
        return self._service_key is not None

    @classmethod
    def using_type(
        cls,
        service_type: type,
        implementation_type: type,
        lifetime: ServiceLifetime,
        service_key: object | None = None,
    ) -> Self:
        """Creates a new instance of `ServiceDescriptor` with the specified `implementationType`.

        Args:
            service_type (type): The type of the service.
            implementation_type (type): The type implementing the service.
            lifetime (ServiceLifetime): The lifetime of the service.
            service_key (object): The key used to identify the service.

        """
        return cls(
            service_type,
            implementation_type=implementation_type,
            lifetime=lifetime,
            service_key=service_key,
        )

    @classmethod
    def using_instance(
        cls,
        service_type: type,
        instance: object,
        service_key: object | None = None,
    ) -> Self:
        """Creates a new instance of `ServiceDescriptor` with the specified `instance`.

        Args:
            service_type (type): The type of the service.
            instance (object): The instance implementing the service.
            service_key (object): The key used to identify the service.

        """
        return cls(
            service_type,
            instance=instance,
            lifetime=ServiceLifetime.SINGLETON,
            service_key=service_key,
        )

    @classmethod
    def using_factory(
        cls,
        service_type: type,
        factory: _Factory,
        lifetime: ServiceLifetime,
        service_key: object | None = None,
    ) -> Self:
        """Creates a new instance of `ServiceDescriptor` with the specified `factory`.

        Args:
            service_type (type): The type of the service.
            factory (Callable): A factory used for creating service instances.
            lifetime (ServiceLifetime): The lifetime of the service.
            service_key (object): The key used to identify the service.

        """
        return cls(
            service_type, factory=factory, lifetime=lifetime, service_key=service_key
        )

    def __str__(self) -> str:
        lifetime = (
            f"service_type: {self.service_type.__name__} lifetime: {self.lifetime.name}"
        )

        if self.is_keyed_service:
            lifetime += f" service_key: {self.service_key}"

            if self.keyed_implementation_type:
                return f"{lifetime} implementation_type: {self.keyed_implementation_type.__name__}"

            if self.keyed_implementation_factory:
                signature = inspect.signature(self.keyed_implementation_factory)
                factory_method = self.keyed_implementation_factory.__name__ + str(
                    signature
                )
                return f"{lifetime} implementation_factory: {factory_method}"

            return f"{lifetime} implementation_instance: {self.keyed_implementation_instance}"
        else:
            if self.implementation_type:
                return f"{lifetime} implementation_type: {self.implementation_type.__name__}"

            if self.implementation_factory:
                signature = inspect.signature(self.implementation_factory)
                factory_method = self.implementation_factory.__name__ + str(signature)
                return f"{lifetime} implementation_factory: {factory_method}"

            return f"{lifetime} implementation_instance: {self.implementation_instance}"

    def get_implementation_type(self) -> type:
        if not self.service_key:
            if self.implementation_type:
                return self.implementation_type
            elif self.implementation_instance:
                return type(self.implementation_instance)
            elif self.implementation_factory:
                return self._get_factory_implementation_type(
                    self.implementation_factory
                )
        else:
            if self.keyed_implementation_type:
                return self.keyed_implementation_type
            elif self.keyed_implementation_instance:
                return type(self.keyed_implementation_instance)
            elif self.keyed_implementation_factory:
                return self._get_factory_implementation_type(
                    self.keyed_implementation_factory
                )

        raise ValueError(
            "implementation_type, implementation_instance, or implementation_factory must be non null"
        )

    @classmethod
    def describe(
        cls,
        service_type: type,
        implementation: type | _Factory,
        lifetime: ServiceLifetime,
        service_key: object | None = None,
    ) -> Self:
        """Creates an instance of `ServiceDescriptor` with the specified
        `service_type`, `implementation`, and `lifetime`. `implementation`
        can be a type or a factory function.

        Args:
            service_type (type): The type of the service.
            implementation (type | Callable): The type of the implementation or a factory function.
            lifetime (ServiceLifetime): The lifetime of the service.
            service_key (object): The key used to identify the service.

        Returns:
            ServiceDescriptor: A new instance of `ServiceDescriptor`.
        """
        if isinstance(implementation, type):
            return cls.using_type(service_type, implementation, lifetime, service_key)
        elif callable(implementation):
            return cls.using_factory(
                service_type, implementation, lifetime, service_key
            )

    @classmethod
    def transient(
        cls, service: type, implementation: type | _ImplementationFactory
    ) -> Self:
        """Creates an instance of `ServiceDescriptor` with the specified
        `service`, `implementation`, and `ServiceLifetime.TRANSIENT` lifetime.
        `implementation` can be a type or a factory function.

        Args:
            service (type): The type of the service.
            implementation (type | Callable): The type of the implementation or a factory function.
        """
        return cls.describe(service, implementation, ServiceLifetime.TRANSIENT)

    @classmethod
    def keyed_transient(
        cls,
        service: type,
        implementation: type | _KeyedImplementationFactory,
        service_key: object | None,
    ) -> Self:
        """Creates an instance of `ServiceDescriptor` with the specified
        `service`, `implementation`, and `ServiceLifetime.TRANSIENT` lifetime.
        `implementation` can be a type or a factory function.

        Args:
            service (type): The type of the service.
            implementation (type | Callable): The type of the implementation or a factory function.
            service_key (object): The key used to identify the service.
        """
        return cls.describe(
            service, implementation, ServiceLifetime.TRANSIENT, service_key
        )

    @classmethod
    def scoped(
        cls, service: type, implementation: type | _ImplementationFactory
    ) -> Self:
        """Creates an instance of `ServiceDescriptor` with the specified
        `service`, `implementation`, and `ServiceLifetime.SCOPED` lifetime.
        `implementation` can be a type or a factory function.

        Args:
            service (type): The type of the service.
            implementation (type | Callable): The type of the implementation
                                              or a factory function.
        """
        return cls.describe(service, implementation, ServiceLifetime.SCOPED)

    @classmethod
    def keyed_scoped(
        cls,
        service: type,
        implementation: type | _KeyedImplementationFactory,
        service_key: object | None,
    ) -> Self:
        """Creates an instance of `ServiceDescriptor` with the specified
        `service`, `implementation`, and `ServiceLifetime.SCOPED` lifetime.
        `implementation` can be a type or a factory function.

        Args:
            service (type): The type of the service.
            implementation (type | Callable): The type of the implementation or a factory function.
            service_key (object): The key used to identify the service.
        """
        return cls.describe(
            service, implementation, ServiceLifetime.SCOPED, service_key
        )

    @classmethod
    def singleton(
        cls, service: type, implementation: type | _ImplementationFactory | object
    ) -> Self:
        """Creates an instance of `ServiceDescriptor` with the specified
        `service`, `implementation`, and `ServiceLifetime.SINGLETON` lifetime.
        `implementation` can be a type, an instance, or a factory function.

        Args:
            service (type): The type of the service.
            implementation (type | object | Callable): The type of the implementation, an instance object,
                                                       or a factory function.
        """
        if implementation is not type and not callable(implementation):
            return cls.using_instance(service, implementation)
        return cls.describe(service, implementation, ServiceLifetime.SINGLETON)

    @classmethod
    def keyed_singleton(
        cls,
        service: type,
        implementation: type | _KeyedImplementationFactory | object,
        service_key: object | None,
    ) -> Self:
        """Creates an instance of `ServiceDescriptor` with the specified
        `service`, `implementation`, and `ServiceLifetime.SINGLETON` lifetime.
        `implementation` can be a type, an instance, or a factory function.

        Args:
            service (type): The type of the service.
            implementation (type | object | Callable): The type of the implementation, an instance object,
                                                       or a factory function.
            service_key (object): The key used to identify the service.
        """
        if implementation is not type and not callable(implementation):
            return cls.using_instance(service, implementation, service_key)
        return cls.describe(
            service, implementation, ServiceLifetime.SINGLETON, service_key
        )

    def _raise_not_keyed_error(self):
        raise RuntimeError("This service descriptor is not keyed.")

    @classmethod
    def _get_factory_implementation_type(cls, factory: _Factory) -> type:
        factory_return_type = inspect.signature(factory).return_annotation
        assert (
            factory_return_type is not inspect.Signature.empty
        ), "Factory must have a return type annotation"
        assert isinstance(
            factory_return_type, type
        ), "Factory return type must be a type"
        return factory_return_type


class ServiceCollectionProto(Protocol):
    """Defines a collection of service descriptors."""

    def __len__(self) -> int: ...

    def index(
        self, value: ServiceDescriptor, start: int = 0, stop: int = sys.maxsize
    ) -> int: ...

    def count(self, value: ServiceDescriptor) -> int: ...

    def __contains__(self, value: object) -> bool: ...

    def __iter__(self) -> Iterator[ServiceDescriptor]: ...

    def __reversed__(self) -> Iterator[ServiceDescriptor]: ...

    def insert(self, index: int, value: ServiceDescriptor) -> None: ...

    @overload
    def __getitem__(self, index: int) -> ServiceDescriptor: ...

    @overload
    def __getitem__(self, index: slice) -> list[ServiceDescriptor]: ...

    def __setitem__(
        self, index: int | slice, value: ServiceDescriptor | Iterable[ServiceDescriptor]
    ) -> None: ...

    @overload
    def __delitem__(self, index: int) -> None: ...

    @overload
    def __delitem__(self, index: slice) -> None: ...

    def append(self, value: ServiceDescriptor) -> None: ...

    def clear(self) -> None: ...

    def copy(self) -> "ServiceCollectionProto": ...

    def extend(self, values: Iterable[ServiceDescriptor]) -> None: ...

    def reverse(self) -> None: ...

    def pop(self, index: int = -1) -> ServiceDescriptor: ...

    def remove(self, value: ServiceDescriptor) -> None: ...

    def __add__(
        self, other: Iterable[ServiceDescriptor]
    ) -> "ServiceCollectionProto": ...

    def __radd__(
        self, other: Iterable[ServiceDescriptor]
    ) -> "ServiceCollectionProto": ...

    def __iadd__(self, values: Iterable[ServiceDescriptor]) -> Self: ...
