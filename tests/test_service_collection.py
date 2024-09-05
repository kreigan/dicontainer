from dicontainer.container import (
    ServiceCollection,
)


def test_new_collection_is_empty(empty_collection: ServiceCollection):
    assert len(empty_collection) == 0


def test_collection_to_readonly(empty_collection: ServiceCollection):
    assert not empty_collection.is_readonly, "New collection must be mutable"
    empty_collection.make_readonly()
    assert empty_collection.is_readonly, "Collection must be read-only"
