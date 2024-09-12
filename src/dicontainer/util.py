import typing

from collections.abc import Iterable
from typing import Any, TypeGuard, TypeVar


# ruff: noqa: ANN401    # Any values are okay in this file


_T = TypeVar("_T")


def is_type(value: Any, expected_type: type[_T]) -> TypeGuard[_T]:
    """Checks if the given value is of the expected type.

    Args:
        value (Any): The value to check.
        expected_type (type[_T]): The expected type.

    Returns:
        bool: True if the value is of the expected type, False otherwise
    """
    origin = typing.get_origin(expected_type)
    if origin is Iterable:
        item_type = typing.get_args(expected_type)[0]
        try:
            return all(isinstance(item, item_type) for item in value)
        except TypeError:
            return False

    return isinstance(value, expected_type)


class Ensure:
    """Utility class for ensuring values meet certain criteria."""

    @staticmethod
    def not_none(value: Any, message: str | None = None) -> None:
        """Ensures the given value is not None or raises a TypeError."""
        if value is None:
            msg = message or "Value cannot be None"
            raise ValueError(msg)

    @staticmethod
    def is_type(value: Any, expected_type: type, message: str | None = None) -> None:
        """Ensures the given value is of the expected type or raises a TypeError."""
        if not is_type(value, expected_type):
            raise TypeError(message or f"Expected {expected_type} but got {value}")
