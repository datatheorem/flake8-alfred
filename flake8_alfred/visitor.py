"""Generic implementation of the Visitor and Dispatcher patterns."""

from collections import ChainMap
from collections.abc import Callable
from inspect import Signature
from types import UnionType
from typing import Any
from typing import Generic
from typing import Self
from typing import TypeVar
from typing import get_args


A = TypeVar("A")
B = TypeVar("B")
T = TypeVar("T")


class RegisterMeta(type):
    """Register metaclass. Classes that are implemented using this metaclass
    have a `shared_dict` property visible to their subclasses, that is a
    mapping of arbitrary keys and values.
    """
    @classmethod
    def __prepare__(
            cls,
            name: str,
            bases: tuple[type[Any], ...],
            /,
            **kwargs: Any,
    ) -> dict[str, object]:
        dicts = (base.shared_dict for base in bases if isinstance(base, cls))
        return {"_shared_dict": ChainMap(*dicts).new_child()}

    @property
    def shared_dict(cls) -> ChainMap:
        """Returns the class shared dict."""
        return cls._shared_dict  # type: ignore


class Visitor(Generic[A, B], metaclass=RegisterMeta):
    """Visitor base class."""
    def generic_visit(self, node: A) -> B:
        """Generic visitor for nodes of unknown type. The default
        implementation raises a TypeError.
        """
        raise TypeError(f"{type(node)} is not registered by {self}")

    @classmethod
    def on(cls, function: Callable[[Self, T], B]) -> Callable[[Self, T], B]:
        """Register a value into the `shared_dict` class attribute."""
        signature = Signature.from_callable(function)
        _, key_tp = signature.parameters.values()
        for type_ in types_in_annotation(key_tp.annotation):
            cls.shared_dict[type_] = function
        return function

    def visit(self: Self, node: A) -> B:
        """Visits a node by calling the registered function for this type of
        nodes.
        """
        for base in type(node).mro():
            try:
                function: Callable[[Self, A], B] = type(self).shared_dict[base]
            except KeyError:
                pass
            else:
                return function(self, node)
        return self.generic_visit(node)


def types_in_annotation(annotation: type[T]) -> tuple[type[T], ...]:
    match annotation:
        case UnionType() as union:
            return get_args(union)
        case type() as simple:
            return (simple,)
        case _:
            assert False
