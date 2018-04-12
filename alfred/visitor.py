"""Flake8 plugin emitting warning for obsolete symbols."""

from collections import ChainMap
from operator import attrgetter

from typing import (
    Any, Callable, ChainMap as ChainMapT, Hashable, Iterable, Optional,
    TypeVar, Union
)


ScopeT = ChainMapT[str, Optional[str]]

T = TypeVar("T")
U = TypeVar("U")


class RegisterMeta(type):
    """Register meta class. Classes that are implemented using this metaclass
    have a `_register` attribute visible to their subclasses, that's a mapping
    of arbitrary keys and values.
    """
    def __new__(mcs, name, bases, namespace, **kwargs):  # type: ignore
        parents = map(attrgetter("_register"), bases)
        register = ChainMap({}, *parents)
        namespace["_register"] = register
        return super().__new__(mcs, name, bases, namespace, **kwargs)

    def register(cls, key: Hashable) -> Callable[[T], T]:
        """Register a value into the `_register` class attribute."""
        def _wrapper(value: T) -> T:
            cls._register[key] = value
            return value
        return _wrapper


class Visitor(metaclass=RegisterMeta):
    """Visitor base class."""
    def generic_visit(self, node: Any) -> Any:
        """Generic visitor for nodes of unknown type. The default
        implementations raises a TypeError.
        """
        raise TypeError(f"{type(node)} is not registered by {self}")

    def visit(self, node: Any) -> Any:
        """Visits a node by calling the registered function for this type of
        nodes.
        """
        cls = first(type(node).mro(), predicate=self._register.__contains__)
        if cls is None:
            return self.generic_visit(node)
        return self._register[cls](self, node)


def first(iterable: Iterable[T],
          predicate: Callable[[T], Any] = None,
          default: U = None) -> Union[T, U, None]:
    """Returns the first item for which predicate is true, or default."""
    return next(filter(predicate, iterable), default)
