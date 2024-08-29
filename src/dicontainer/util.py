from collections.abc import Iterable
from typing import Any, TypeVar


_T = TypeVar("_T")


def is_iterable(value: Any) -> bool:
    """Checks if the given value is an iterable.

    Args:
        value (Any): The value to check.

    Returns:
        bool: True if the value is an iterable, False otherwise
    """
    try:
        iter(value)
        return True
    except TypeError:
        return False


class Ensure:
    """Utility class for ensuring values meet certain criteria."""

    @staticmethod
    def not_none(value: Any, message: str | None = None) -> None:
        """Ensures the given value is not None or raises a TypeError."""
        if value is None:
            msg = message or "Value cannot be None"
            raise TypeError(msg)

    @staticmethod
    def is_type(value: Any, expected_type: type, message: str | None = None) -> None:
        """Ensures the given value is of the expected type or raises a TypeError."""
        valid = True

        if isinstance(expected_type, Iterable):
            valid = is_iterable(value)
        else:
            valid = isinstance(value, expected_type)

        if not valid:
            raise TypeError(message or f"Expected {expected_type} but got {type(value)}")

    @staticmethod
    def is_iterable(value: Any, message: str | None = None) -> None:
        """Ensures the given value is an iterable or raises a TypeError."""
        Ensure.is_type(value, Iterable, message)

    @staticmethod
    def all_in_iterable(iterable: Iterable[_T], expected_type: _T, message: str | None = None) -> None:
        """Ensures all values in the given iterable are of the expected type or raises a TypeError."""
        Ensure.is_iterable(iterable)
        for item in iterable:
            Ensure.is_type(item, type(expected_type), message)
