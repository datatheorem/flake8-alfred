"""Generic implementation of the Visitor and Dispatcher patterns."""

from collections import ChainMap
from operator import attrgetter
from typing import Any, Callable, ChainMap as ChainMapT, Hashable, TypeVar


T = TypeVar("T")


class RegisterMeta(type):
    """Register meta class. Classes that are implemented using this metaclass
    have a `_register` attribute visible to their subclasses, that's a mapping
    of arbitrary keys and values.
    """
    def __new__(mcs, name, bases, namespace, **kwargs):    # type: ignore
        parents = map(attrgetter("_register"), bases)
        register = ChainMap({}, *parents)
        namespace["_register"] = register
        return super().__new__(mcs, name, bases, namespace, **kwargs)

    @property
    def register(cls) -> ChainMapT[Hashable, Any]:
        """Returns this class register."""
        return cls._register                               # type: ignore


class Dispatcher(metaclass=RegisterMeta):
    """Dispatcher base class."""
    @classmethod
    def dispatch(cls, key: Hashable) -> Any:
        """Returns the item associated with `key` or raise `KeyError`."""
        return cls.register[key]

    @classmethod
    def on(cls, key: Hashable) -> Callable[[T], T]:
        """Register a value into the `_register` class attribute."""
        def _wrapper(value: T) -> T:
            cls.register[key] = value
            return value
        return _wrapper


class Visitor(Dispatcher):
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
        for base in type(node).mro():
            try:
                function = type(self).dispatch(base)
            except KeyError:
                pass
            else:
                return function(self, node)
        return self.generic_visit(node)
