from typing import Any, cast

import pytest

from dicontainer.container import (
    ServiceCollection,
    ServiceDescriptor,
)
from tests.fixtures.service_collection import ServiceCollectionFactory
from tests.fixtures.service_descriptor import ServiceFactory


def test_new_collection_is_empty(empty_collection: ServiceCollection):
    assert len(empty_collection) == 0


def test_collection_to_readonly(empty_collection: ServiceCollection):
    assert not empty_collection.is_readonly, "New collection must be mutable"
    empty_collection.make_readonly()
    assert empty_collection.is_readonly, "Collection must be read-only"


@pytest.mark.parametrize(
    ("method", "args"),
    [
        pytest.param("insert", (0, None), id="insert"),
        pytest.param("__setitem__", (0, None), id="__setitem__"),
        pytest.param("__delitem__", (0,), id="__delitem__"),
        pytest.param("append", (None,), id="append"),
        pytest.param("clear", (), id="clear"),
        pytest.param("extend", (None,), id="extend"),
        pytest.param("reverse", (), id="reverse"),
        pytest.param("pop", (0,), id="pop"),
        pytest.param("remove", (None,), id="remove"),
        pytest.param("__iadd__", (None,), id="__iadd__"),
    ],
)
def test_cannot_modify_readonly(
    empty_collection: ServiceCollection, method: str, args: tuple[Any]
):
    empty_collection.make_readonly()
    with pytest.raises(RuntimeError, match="cannot be modified"):
        getattr(empty_collection, method)(*args)


def test_index(collection_factory: ServiceCollectionFactory):
    service = collection_factory.service_factory.singleton.instance()
    collection = collection_factory.singleton_instance(service)
    assert collection.index(service) == 0


def test_count(collection_factory: ServiceCollectionFactory):
    service = collection_factory.service_factory.singleton.instance()
    collection = collection_factory.singleton_instance(service)
    assert collection.count(service) == 1


def test_contains(collection_factory: ServiceCollectionFactory):
    service = collection_factory.service_factory.singleton.instance()
    collection = collection_factory.singleton_instance(service)
    assert service in collection


def test_reversed(
    empty_collection: ServiceCollection,
    service_factory: ServiceFactory,
):
    service_1 = service_factory.singleton.instance()
    service_2 = service_factory.singleton.instance()

    empty_collection.append(service_1)
    empty_collection.append(service_2)

    reversed_collection = list(reversed(empty_collection))

    assert len(reversed_collection) == 2
    assert reversed_collection[0] == service_2
    assert reversed_collection[1] == service_1


def test_insert(empty_collection: ServiceCollection, service_factory: ServiceFactory):
    with pytest.raises(TypeError, match=f"Expected {ServiceDescriptor} but got {int}"):
        empty_collection.insert(0, int)  # pyright: ignore[reportArgumentType]

    service = service_factory.singleton.instance()
    empty_collection.insert(0, service)
    assert empty_collection[0] == service

    service_2 = service_factory.singleton.instance()
    assert service_2 != service

    empty_collection.insert(0, service_2)
    assert empty_collection[0] == service_2


def test_try_add(
    empty_collection: ServiceCollection,
    service_factory: ServiceFactory,
):
    service = service_factory.singleton.instance()

    assert len(empty_collection) == 0, "Collection must be empty"

    empty_collection.try_add(service)

    assert len(empty_collection) == 1, "Service must be added to the collection"
    assert service in empty_collection, "Service must be in the collection"

    empty_collection.try_add(service)

    assert len(empty_collection) == 1, "Service must not be added repeatedely"


def test_try_add_keyed(
    empty_collection: ServiceCollection,
    service_factory: ServiceFactory,
):
    factory = service_factory.singleton
    service_key = "service_1"
    service_1 = factory.with_key(service_key).instance()
    assert service_1.service_key == service_key, "Service must have a key"

    assert len(empty_collection) == 0, "Collection must be empty"
    empty_collection.try_add(service_1)

    assert len(empty_collection) == 1, "Service must be added to the collection"
    assert service_1 in empty_collection, "Service must be in the collection"

    service_2 = factory.with_key(service_key).instance()
    assert service_2.service_key == service_key, "Services must have the same key"
    assert (
        service_2.service_type != service_1.service_type
    ), "Service must have a different type"
    empty_collection.try_add(service_2)

    assert len(empty_collection) == 2, "Service with another type must be added"

    service_3 = factory.with_key("service_3").instance(service_2.service_type)
    assert service_3.service_key != service_key, "Service must have a different key"
    assert (
        service_3.service_type == service_2.service_type
    ), "Service must have the same type"
    empty_collection.try_add(service_3)

    assert len(empty_collection) == 3, "Service with another key must be added"


def test_replace(collection_factory: ServiceCollectionFactory):
    collection = collection_factory.get_collection()
    with pytest.raises(ValueError, match="cannot be None"):
        collection.replace(cast(ServiceDescriptor, None))

    assert len(collection) == 0, "Collection must be empty"

    keyed_singleton = collection_factory.service_factory.singleton.with_key("key_1")
    service = keyed_singleton.instance()
    collection.replace(service)

    assert len(collection) == 1, "New service must be added"
    assert collection[0] == service

    similar_service = keyed_singleton.i_type(collection[0].service_type)
    collection.replace(similar_service)

    assert len(collection) == 1, "Service must be replaced"
    assert collection[0] == similar_service

    different_service = keyed_singleton.with_key("key_2").i_type()
    collection.replace(different_service)

    assert len(collection) == 2, "Service with new key must be added"


def test_remove_all(collection_factory: ServiceCollectionFactory):
    collection = collection_factory.get_collection()
    singleton_factory = collection_factory.service_factory.singleton
    service = singleton_factory.instance()

    collection += [service, service, service]
    assert len(collection) == 3, "Collection must have 3 services"

    collection.remove_all(service.service_type)
    assert len(collection) == 0, "All services must be removed"

    service = singleton_factory.with_key("some_key").instance()
    collection += [service, service, service]
    assert len(collection) == 3, "Collection must have 3 services"

    collection.remove_all(service.service_type)
    assert len(collection) == 3, "Services with different keys must not be removed"

    collection.remove_all(service.service_type, "some_key")
    assert len(collection) == 0, "All services must be removed"
