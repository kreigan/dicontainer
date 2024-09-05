import inspect
import sys

from abc import abstractmethod
from collections.abc import Iterable, MutableSequence
from enum import Enum
from functools import partial
from typing import Callable, Iterator, Protocol, TypeVar, cast, overload

from typing_extensions import Self

from .util import Ensure


class ServiceLifetime(Enum):
    """Specifies the lifetime of a service in a `ServiceCollection`."""

    SINGLETON = 0
    """Specifies that a single instance of the service will be created."""

    SCOPED = 1
    """Specifies that a new instance of the service will be created for each scope."""

    TRANSIENT = 2
    """Specifies that a new instance of the service will be created every time it is requested."""


class ServiceProvider(Protocol):
    """Defines a mechanism for retrieving a service object."""

    @abstractmethod
    def get_service(self, service_type: type) -> object | None:
        """Gets the service object of the specified type.

        Args:
            service_type (type): An object that specifies the type of service object to get.

        Returns:
            object: A service object, or `None` if there is no service object of type `service_type`.
        """
        raise NotImplementedError


TService = TypeVar("TService", bound=object, covariant=True)
TImplementation = TypeVar("TImplementation", bound=object, covariant=True)

_ImplementationFactory = Callable[[ServiceProvider], object]
_KeyedImplementationFactory = Callable[[ServiceProvider, object | None], object]
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


class ServiceCollection(MutableSequence[ServiceDescriptor]):
    """Defines a collection of service descriptors."""

    def __init__(self) -> None:
        self._descriptors: list[ServiceDescriptor] = []
        self._readonly = False

    @property
    def is_readonly(self) -> bool:
        """Gets a value indicating whether this collection is read-only."""
        return self._readonly

    def make_readonly(self) -> None:
        """Makes this collection read-only. After the collection is marked as
        read-only, any further attempt to modify it throws a `RuntimeError`.

        """
        self._readonly = True

    def _check_readonly(self) -> None:
        if self._readonly:
            raise RuntimeError(
                "The service collection cannot be modified because it is read-only."
            )

    def __len__(self) -> int:
        return len(self._descriptors)

    ### Sequence implementation

    def index(
        self, value: ServiceDescriptor, start: int = 0, stop: int = sys.maxsize
    ) -> int:
        Ensure.is_type(value, ServiceDescriptor)
        return self._descriptors.index(value, start, stop)

    def count(self, value: ServiceDescriptor) -> int:
        Ensure.is_type(value, ServiceDescriptor)
        return self._descriptors.count(value)

    def __contains__(self, value: object) -> bool:
        Ensure.not_none(value)
        return value in self._descriptors

    def __iter__(self) -> Iterator[ServiceDescriptor]:
        return iter(self._descriptors)

    def __reversed__(self) -> Iterator[ServiceDescriptor]:
        return reversed(self._descriptors)

    ### MutableSequence implementation

    def insert(self, index: int, value: ServiceDescriptor) -> None:
        self._check_readonly()
        Ensure.is_type(value, ServiceDescriptor)
        self._descriptors.insert(index, value)

    @overload
    def __getitem__(self, index: int) -> ServiceDescriptor: ...

    @overload
    def __getitem__(self, index: slice) -> list[ServiceDescriptor]: ...

    def __getitem__(
        self, index: int | slice
    ) -> ServiceDescriptor | list[ServiceDescriptor]:
        return self._descriptors[index]

    @overload
    def __setitem__(self, index: int, value: ServiceDescriptor) -> None: ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[ServiceDescriptor]) -> None: ...

    def __setitem__(
        self, index: int | slice, value: ServiceDescriptor | Iterable[ServiceDescriptor]
    ) -> None:
        self._check_readonly()
        if isinstance(index, int):
            Ensure.is_type(value, ServiceDescriptor)
            self._descriptors[index] = cast(ServiceDescriptor, value)
        else:
            value = cast(Iterable[ServiceDescriptor], value)
            Ensure.all_in_iterable(value, ServiceDescriptor)
            self._descriptors[index] = value

    @overload
    def __delitem__(self, index: int) -> None: ...

    @overload
    def __delitem__(self, index: slice) -> None: ...

    def __delitem__(self, index: int | slice) -> None:
        self._check_readonly()
        del self._descriptors[index]

    def append(self, value: ServiceDescriptor) -> None:
        self._check_readonly()
        Ensure.is_type(value, ServiceDescriptor)
        self._descriptors.append(value)

    def clear(self) -> None:
        self._check_readonly()
        self._descriptors.clear()

    def extend(self, values: Iterable[ServiceDescriptor]) -> None:
        self._check_readonly()
        Ensure.all_in_iterable(values, ServiceDescriptor)
        self._descriptors.extend(values)

    def reverse(self) -> None:
        self._check_readonly()
        self._descriptors.reverse()

    def pop(self, index: int = -1) -> ServiceDescriptor:
        self._check_readonly()
        return self._descriptors.pop(index)

    def remove(self, value: ServiceDescriptor) -> None:
        self._check_readonly()
        Ensure.is_type(value, ServiceDescriptor)
        self._descriptors.remove(value)

    def __iadd__(self, values: Iterable[ServiceDescriptor]) -> Self:
        self._check_readonly()
        Ensure.all_in_iterable(values, ServiceDescriptor)
        self._descriptors += values
        return self

    def try_add(self, descriptor: ServiceDescriptor) -> None:
        """Adds the specified `descriptor` to the collection if the service
        type hasn't already been registered.

        Args:
            descriptor (ServiceDescriptor): The service descriptor to add.
        """
        Ensure.not_none(descriptor)
        if any(
            d.service_type == descriptor.service_type
            and d.service_key == descriptor.service_key
            for d in self
        ):
            return

        self.append(descriptor)

    def try_add_many(self, descriptors: Iterable[ServiceDescriptor]) -> None:
        """Adds the specified `descriptors` to the collection if the service
        type hasn't already been registered.

        Args:
            service (type): The type of the service.
            descriptors (Iterable[ServiceDescriptor]): The service descriptors to add.
        """
        Ensure.not_none(descriptors)
        for descriptor in descriptors:
            self.try_add(descriptor)

    def try_add_transient(
        self, service: type, implementation: type | _ImplementationFactory | None = None
    ) -> None:
        """Adds the specified `service` as a `ServiceLifetime.Transient` service
        to the collection if the service type hasn't already been registered. If
        `implementation` is `None`, the service type is used as the implementation.

        Args:
            service (type): The type of the service.
            implementation (type | Callable): The type of the implementation or a factory function.
        """
        descriptor = ServiceDescriptor.transient(service, implementation or service)
        self.try_add(descriptor)

    def try_add_scoped(
        self, service: type, implementation: type | _ImplementationFactory | None = None
    ) -> None:
        """Adds the specified `service` as a `ServiceLifetime.Scoped` service
        to the collection if the service type hasn't already been registered. If
        `implementation` is `None`, the service type is used as the implementation.

        Args:
            service (type): The type of the service.
            implementation (type | Callable): The type of the implementation or a factory function.
        """
        descriptor = ServiceDescriptor.scoped(service, implementation or service)
        self.try_add(descriptor)

    def try_add_singleton(
        self, service: type, implementation: type | _ImplementationFactory | None = None
    ) -> None:
        """Adds the specified `service` as a `ServiceLifetime.Singleton` service
        to the collection if the service type hasn't already been registered. If
        `implementation` is `None`, the service type is used as the implementation.

        Args:
            service (type): The type of the service.
            implementation (type | object | Callable): The type of the implementation, an instance object,
                                                       or a factory function.
        """
        descriptor = ServiceDescriptor.singleton(service, implementation or service)
        self.try_add(descriptor)

    def try_add_enumerable(
        self, descriptor: ServiceDescriptor | Iterable[ServiceDescriptor]
    ) -> None:
        """Adds a `ServiceDescriptor` if an existing descriptor with the same
        `service_type` and an implementation that does not already exist in the
        collection.

        Use this method when registering a service implementation of a service
        type that supports multiple registrations of the same service type.
        Using `append` or `extend` is not idempotent and can add duplicate
        `ServiceDescriptor` instances if called twice. Using `try_add_enumerable`
        will prevent registration of multiple implementation types.

        Args:
            descriptor (ServiceDescriptor | Iterable[ServiceDescriptor]): The service descriptor(s) to add.
        """

        def _try_add_enumerable(descriptor: ServiceDescriptor) -> None:
            Ensure.is_type(descriptor, ServiceDescriptor)

            implementation_type = descriptor.get_implementation_type()

            if (
                implementation_type is object
                or implementation_type is descriptor.service_type
            ):
                raise ValueError(
                    "Implementation type cannot be '{0}' because it is indistinguishable from other services registered for '{1}'.".format(
                        implementation_type, descriptor.service_type
                    )
                )

            for service in self:
                if (
                    service.service_type == descriptor.service_type
                    and service.get_implementation_type() == implementation_type
                    and service.service_key == descriptor.service_key
                ):
                    return

            self.append(descriptor)

        Ensure.not_none(descriptor)

        if isinstance(descriptor, Iterable):
            for d in descriptor:
                _try_add_enumerable(d)
        else:
            _try_add_enumerable(descriptor)

    def replace(self, descriptor: ServiceDescriptor) -> Self:
        """Removes the first service in collection with the same service type
        as `descriptor` and adds `descriptor` to the collection.

        Args:
            descriptor (ServiceDescriptor): The `ServiceDescriptor` to replace with.

        Returns:
            ServiceCollection: The current service collection for chaining.
        """
        Ensure.not_none(descriptor)

        for i, service in enumerate(self):
            if (
                service.service_type == descriptor.service_type
                and service.service_key == descriptor.service_key
            ):
                del self[i]
                break

        self.append(descriptor)
        return self

    def remove_all(self, service_type: type) -> Self:
        """Removes all services of type `service_type` in collection.

        Args:
            service_type (type): The service type to remove.

        Returns:
            ServiceCollection: The current service collection for chaining.
        """
        Ensure.not_none(service_type)
        for i, service in enumerate(self):
            if service.service_type == service_type and service.service_key is None:
                del self[i]

        return self

    def _add(
        self,
        service_type: type,
        implementation: type | _ImplementationFactory,
        lifetime: ServiceLifetime,
    ) -> Self:
        if isinstance(implementation, type):
            descriptor = ServiceDescriptor(
                service_type, implementation_type=implementation, lifetime=lifetime
            )
        else:
            descriptor = ServiceDescriptor(
                service_type, factory=implementation, lifetime=lifetime
            )

        self.append(descriptor)
        return self

    def add_transient(
        self,
        service_type: type,
        implementation: type | _ImplementationFactory | None = None,
    ) -> Self:
        """Adds a transient service of the type specified in `service_type` with an
        implementation of the type or factory specified in `implementation`. If
        `implementation` is `None`, the service type is used as the implementation.

        Args:
            service_type (type): The type of the service.
            implementation (type | Callable | None): The type of the implementation or the factory that creates the service.

        Returns:
            ServiceCollection: The current service collection for chaining.
        """

        Ensure.not_none(service_type)
        return self._add(
            service_type, implementation or service_type, ServiceLifetime.TRANSIENT
        )

    def add_scoped(
        self,
        service_type: type,
        implementation: type | _ImplementationFactory | None = None,
    ) -> Self:
        """Adds a scoped service of the type specified in `service_type` with an
        implementation of the type or factory specified in `implementation`. If
        `implementation` is `None`, the service type is used as the implementation.

        Args:
            service_type (type): The type of the service.
            implementation (type | Callable | None): The type of the implementation or the factory that creates the service.

        Returns:
            ServiceCollection: The current service collection for chaining.
        """

        Ensure.not_none(service_type)
        return self._add(
            service_type, implementation or service_type, ServiceLifetime.SCOPED
        )

    def add_singleton(
        self,
        service_type: type,
        implementation: type | _ImplementationFactory | object | None = None,
    ) -> Self:
        """Adds a singleton service of the type specified in `service_type` with an
        implementation of the type or factory specified in `implementation`. If
        `implementation` is `None`, the service type is used as the implementation.

        Args:
            service_type (type): The type of the service.
            implementation (type | Callable | object | None): The type of the implementation,
                the factory that creates the service, or an instance of the service.

        Returns:
            ServiceCollection: The current service collection for chaining.
        """

        Ensure.not_none(service_type)

        self.append(
            ServiceDescriptor.singleton(service_type, implementation or service_type)
        )
        return self
