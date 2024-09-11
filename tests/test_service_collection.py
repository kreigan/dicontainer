from typing import Any

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
    service = collection_factory.service_factory.singleton.with_instance()
    collection = collection_factory.singleton_instance(service)
    assert collection.index(service) == 0


def test_count(collection_factory: ServiceCollectionFactory):
    service = collection_factory.service_factory.singleton.with_instance()
    collection = collection_factory.singleton_instance(service)
    assert collection.count(service) == 1


def test_contains(collection_factory: ServiceCollectionFactory):
    service = collection_factory.service_factory.singleton.with_instance()
    collection = collection_factory.singleton_instance(service)
    assert service in collection


def test_reversed(
    empty_collection: ServiceCollection,
    service_factory: ServiceFactory,
):
    service_factory.service_type = None

    service_1 = service_factory.singleton.with_instance()
    service_2 = service_factory.singleton.with_instance()

    empty_collection.append(service_1)
    empty_collection.append(service_2)

    reversed_collection = list(reversed(empty_collection))

    assert len(reversed_collection) == 2
    assert reversed_collection[0] == service_2
    assert reversed_collection[1] == service_1


def test_insert(empty_collection: ServiceCollection, service_factory: ServiceFactory):
    with pytest.raises(TypeError, match=f"Expected {ServiceDescriptor} but got {int}"):
        empty_collection.insert(0, int)  # pyright: ignore[reportArgumentType]

    service = service_factory.singleton.with_instance()
    empty_collection.insert(0, service)
    assert empty_collection[0] == service

    service_factory.service_type = None
    service_2 = service_factory.singleton.with_instance()
    empty_collection.insert(0, service_2)
    assert empty_collection[0] == service_2
