import typing

from collections.abc import Iterable
from typing import Any, TypeGuard, TypeVar


# ruff: noqa: ANN401    # Any values are okay in this file


_T = TypeVar("_T")


def is_iterable(value: Any, t: type[_T]) -> TypeGuard[Iterable[_T]]:
    """Checks if the given value is an iterable.

    Args:
        value (Any): The value to check.

    Returns:
        bool: True if the value is an iterable, False otherwise
    """
    try:
        return all(isinstance(item, t) for item in value)
    except TypeError:
        return False


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
        valid = True

        origin = typing.get_origin(expected_type)
        if origin is Iterable:
            valid = is_iterable(value, typing.get_args(expected_type)[0])
        else:
            valid = isinstance(value, expected_type)

        if not valid:
            raise TypeError(message or f"Expected {expected_type} but got {value}")

    @staticmethod
    def is_iterable(value: Any, t: type[_T], message: str | None = None) -> None:
        """Ensures the given value is an iterable or raises a TypeError."""
        Ensure.is_type(value, t, message)
