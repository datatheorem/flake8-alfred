"""Symbols visitor: list all qualified names in a given AST."""

import builtins

from ast import (
    # Generic AST type
    AST,
    # Special
    arg, arguments, comprehension, ExceptHandler, expr, stmt,
    # Statements
    AsyncFunctionDef, ClassDef, FunctionDef, Import, ImportFrom,
    # Expressions
    Attribute, DictComp, GeneratorExp, Lambda, ListComp, Name, SetComp,
    # Expression context
    Del, Param, Store,
    # Visitors
    iter_child_nodes
)

from typing import (
    Any, ChainMap as ChainMapT, Iterator, Mapping, Optional, Sequence, Tuple,
    Union
)

from collections import ChainMap
from contextlib import contextmanager

from alfred.visitor import Visitor


Function = Union[AsyncFunctionDef, FunctionDef]
ScopeT = ChainMapT[str, Optional[str]]
Symbols = Iterator[Tuple[str, Union[expr, stmt]]]
UnaryComp = Union[GeneratorExp, ListComp, SetComp]


class SymbolsVisitor(Visitor):
    """SymbolsVisitor.visit yields a pair (qualified_name, node) for all
    qualified names it finds in the given AST.

    It does handle:
        - Imports: Importing an obsolete symbol will yield it;
        - Delete statements: (del obsolete_symbol; obsolete symbol) doesn't
          yields anything;
        - Scopes: If you overwrite a symbol in a given function or class scope,
          it will not be overwriten in outer scopes;
        - Type annotations.

    We don't support global and nonlocal statements for now, and the assignment
    operator untrack the symbol if it's on the left hand side, no matter what's
    on the right hand side.
    """
    def __init__(self) -> None:
        # Load names from the builtins module into self.scopes. If they are
        # not overwritten, each builtin name is an alias of itself
        # (self.scopes["print"] == "print")
        init = dir(builtins)
        self.scopes: ScopeT = ChainMap(dict(zip(init, init)))

    @contextmanager
    def scope(self) -> Iterator[Mapping[str, Any]]:
        """Context manager that create a new scope (that is, add a mapping into
        self.scopes) and delete it on exit."""
        self.scopes = self.scopes.new_child()
        try:
            yield self.scopes.maps[0]
        finally:
            self.scopes = self.scopes.parents

    def generic_visit(self, node: AST) -> Symbols:
        """Equivalent to ast.NodeVisitor.visit, except it chains the returned
        iterators.
        """
        for child in iter_child_nodes(node):
            yield from self.visit(child)


# HELPERS


def visit_optional(vtor: Visitor, node: Optional[Any]) -> Iterator[Any]:
    """Visit an optional node."""
    if node is not None:
        yield from vtor.visit(node)


def visit_sequence(vtor: Visitor, node: Sequence[Any]) -> Iterator[Any]:
    """Visit a sequence/list of nodes."""
    for item in node:
        yield from vtor.visit(item)


# SPECIAL


@SymbolsVisitor.on(arg)
def visit_arg(vtor: SymbolsVisitor, node: arg) -> Symbols:
    """Visit the annotation if any, remove the symbol from the context."""
    yield from visit_optional(vtor, node.annotation)
    vtor.scopes[node.arg] = None


@SymbolsVisitor.on(arguments)
def visit_arguments(vtor: SymbolsVisitor, node: arguments) -> Symbols:
    """Visit the defaults values first, then the arguments names."""
    yield from visit_sequence(vtor, node.kw_defaults)
    yield from visit_sequence(vtor, node.defaults)
    yield from visit_sequence(vtor, node.kwonlyargs)
    yield from visit_sequence(vtor, node.args)
    yield from visit_optional(vtor, node.kwarg)
    yield from visit_optional(vtor, node.vararg)


@SymbolsVisitor.on(comprehension)
def visit_comprehension(vtor: SymbolsVisitor, node: comprehension) -> Symbols:
    """Visit the iterable expression, then the target name, then the
    predicates.
    """
    yield from vtor.visit(node.iter)
    yield from vtor.visit(node.target)
    yield from visit_sequence(vtor, node.ifs)


@SymbolsVisitor.on(ExceptHandler)
def visit_except_handler(vtor: SymbolsVisitor, node: ExceptHandler) -> Symbols:
    """Visit the exception type, remove the alias from the context then
    visit the body.
    """
    yield from visit_optional(vtor, node.type)
    if node.name is not None:
        vtor.scopes[node.name] = None
    yield from visit_sequence(vtor, node.body)


# STATEMENTS


@SymbolsVisitor.on(ClassDef)
def visit_class_def(vtor: SymbolsVisitor, node: ClassDef) -> Symbols:
    """Visit in the following order:
        Decorators; Base classes; Keywords; Remove name from context; Body.
    """
    yield from visit_sequence(vtor, node.decorator_list)
    yield from visit_sequence(vtor, node.bases)
    yield from visit_sequence(vtor, node.keywords)
    vtor.scopes[node.name] = None
    with vtor.scope():
        yield from visit_sequence(vtor, node.body)


@SymbolsVisitor.on(AsyncFunctionDef)
@SymbolsVisitor.on(FunctionDef)
def visit_function(vtor: SymbolsVisitor, node: Function) -> Symbols:
    """Visit a function definition in the following order:
        Decorators; Return annotation; Arguments default values;
        Remove name from context; Arguments names; Function body.
    """
    yield from visit_sequence(vtor, node.decorator_list)
    yield from visit_optional(vtor, node.returns)
    yield from visit_sequence(vtor, node.args.kw_defaults)
    yield from visit_sequence(vtor, node.args.defaults)
    vtor.scopes[node.name] = None
    with vtor.scope():
        yield from visit_sequence(vtor, node.args.kwonlyargs)
        yield from visit_sequence(vtor, node.args.args)
        yield from visit_optional(vtor, node.args.kwarg)
        yield from visit_optional(vtor, node.args.vararg)
        yield from visit_sequence(vtor, node.body)


@SymbolsVisitor.on(Import)
def visit_import(vtor: SymbolsVisitor, node: Import) -> Symbols:
    """Add the module to the current context."""
    for alias in node.names:
        vtor.scopes[alias.asname or alias.name] = alias.name
        yield (alias.name, node)


@SymbolsVisitor.on(ImportFrom)
def visit_import_from(vtor: SymbolsVisitor, node: ImportFrom) -> Symbols:
    """Add the symbols to the current context."""
    for alias in node.names:
        module = node.module or ""
        qualified = f"{module}.{alias.name}"
        vtor.scopes[alias.asname or alias.name] = qualified
        yield (qualified, node)


# EXPRESSIONS


@SymbolsVisitor.on(Attribute)
def visit_attribute(vtor: SymbolsVisitor, node: Attribute) -> Symbols:
    """Postfix the seen symbols."""
    for lhs, _ in vtor.visit(node.value):
        yield (f"{lhs}.{node.attr}", node)


@SymbolsVisitor.on(DictComp)
def visit_dict_comp(vtor: SymbolsVisitor, node: DictComp) -> Symbols:
    """Same as visit_unary_comp, except here we have a key and a value."""
    with vtor.scope():
        yield from visit_sequence(vtor, node.generators)
        yield from vtor.visit(node.key)
        yield from vtor.visit(node.value)


@SymbolsVisitor.on(Lambda)
def visit_lambda(vtor: SymbolsVisitor, node: Lambda) -> Symbols:
    """Visit the arguments first, then the body."""
    with vtor.scope():
        yield from vtor.visit(node.args)
        yield from vtor.visit(node.body)


@SymbolsVisitor.on(Name)
def visit_name(vtor: SymbolsVisitor, node: Name) -> Symbols:
    """If the symbol is getting overwritten, then delete it from the context,
    else yield it if it's known in this context.
    """
    if isinstance(node.ctx, (Del, Param, Store)):
        vtor.scopes[node.id] = None
    name = vtor.scopes.get(node.id)
    if name is not None:
        yield (name, node)


@SymbolsVisitor.on(GeneratorExp)
@SymbolsVisitor.on(ListComp)
@SymbolsVisitor.on(SetComp)
def visit_unary_comp(vtor: SymbolsVisitor, node: UnaryComp) -> Symbols:
    """Visit the generators expressions, then the left element, the whole being
    wrapped into a new context.
    """
    with vtor.scope():
        yield from visit_sequence(vtor, node.generators)
        yield from vtor.visit(node.elt)
