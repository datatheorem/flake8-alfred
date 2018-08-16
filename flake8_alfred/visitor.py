"""Generic implementation of the Visitor and Dispatcher patterns."""

from collections import ChainMap

from typing import (
    Any, Callable, ChainMap as ChainMapT, Dict,
    Generic, Hashable, Tuple, Type, TypeVar
)


A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")


class RegisterMeta(type):
    """Register metaclass. Classes that are implemented using this metaclass
    have a `shared_dict` property visible to their subclasses, that is a
    mapping of arbitrary keys and values.
    """
    @classmethod
    def __prepare__(cls, name: str, bases: Tuple[Type], **kwargs: Any) -> Dict:
        dicts = (base.shared_dict for base in bases if isinstance(base, cls))
        return {"_shared_dict": ChainMap(*dicts).new_child()}

    @property
    def shared_dict(cls) -> ChainMapT:
        """Returns the class shared dict."""
        return cls._shared_dict  # type: ignore


# This class is useless since python 3.7 because GenericMeta was removed in
# that version and Generic is now an instance of type. Before that this class
# was needed because Dispatcher had to be an instance of both RegisterMeta and
# GenericMeta since it subclass Generic.

class GenericRegisterMeta(RegisterMeta, type(Generic)):  # type: ignore
    """Generic-compatible version of RegisterMeta."""


class Dispatcher(Generic[A, B], metaclass=GenericRegisterMeta):
    """Dispatcher base class."""
    def dispatch(self, key: A) -> B:
        """Returns the item associated with `key` or raise `KeyError`."""
        return type(self).shared_dict[key]

    @classmethod
    def on(cls, key: Hashable) -> Callable[[C], C]:
        """Register a value into the `shared_dict` class attribute."""
        def _wrapper(value: C) -> C:
            cls.shared_dict[key] = value
            return value
        return _wrapper


class Visitor(Dispatcher[Type[A], Callable[["Visitor[A, B]", A], B]]):
    """Visitor base class."""
    def generic_visit(self, node: A) -> B:
        """Generic visitor for nodes of unknown type. The default
        implementation raises a TypeError.
        """
        raise TypeError(f"{type(node)} is not registered by {self}")

    def visit(self, node: A) -> B:
        """Visits a node by calling the registered function for this type of
        nodes.
        """
        for base in type(node).mro():
            try:
                function = self.dispatch(base)
            except KeyError:
                pass
            else:
                return function(self, node)
        return self.generic_visit(node)
