"""Flake8 plugin emitting warning for obsolete symbols."""

import builtins

from ast import (
    # Generic AST type
    AST,
    # Special
    arg, expr, stmt,
    # Statements
    AsyncFunctionDef, ClassDef, FunctionDef, Import, ImportFrom,
    # Expressions
    Attribute, Name,
    # Expression context
    Del, Param, Store,
    # Visitors
    iter_child_nodes
)

from typing import (
    Any, ChainMap as ChainMapT, Dict, Iterator, Mapping, Optional, Sequence,
    Tuple, Union
)

from collections import ChainMap
from contextlib import contextmanager

from pkg_resources import get_distribution


__version__ = get_distribution(__name__).version

FlakeError = Tuple[int, int, str, type]
ScopeT = ChainMapT[str, Optional[str]]
Symbols = Iterator[Tuple[str, Union[expr, stmt]]]


class QualifiedNamesVisitor:
    """QualifiedNamesVisitor.visit yields a pair (qualified_name, node) for all
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
        # Load names from the builtins module into self._scopes. If they are
        # not overwritten, each builtin name is an alias of himself
        # (self._scopes["print"] == "print").
        init = dir(builtins)
        self._scopes: ScopeT = ChainMap(dict(zip(init, init)))

    @contextmanager
    def scope(self) -> Iterator[Mapping[str, Any]]:
        """Context manager that create a new scope (that is, add a mapping into
        self._scopes) and delete it on exit."""
        self._scopes = self._scopes.new_child()
        try:
            yield self._scopes.maps[0]
        finally:
            self._scopes = self._scopes.parents

    def visit(self, node: AST) -> Symbols:
        """Equivalent to ast.NodeVisitor.visit."""
        typename = type(node).__name__
        return getattr(self, f"visit_{typename}", self.generic_visit)(node)

    def generic_visit(self, node: AST) -> Symbols:
        """Equivalent to ast.NodeVisitor.visit, except it chains the returned
        iterators.
        """
        for child in iter_child_nodes(node):
            yield from self.visit(child)

    # SPECIAL

    def visit_arg(self, node: arg) -> Symbols:
        """Visit the annotation if any, remove the symbol from the context."""
        yield from self.visit_optional(node.annotation)
        self._scopes[node.arg] = None

    def visit_optional(self, node: Optional[AST]) -> Symbols:
        """Visit an optional node."""
        if node is not None:
            yield from self.visit(node)

    def visit_sequence(self, node: Sequence[AST]) -> Symbols:
        """Visit a sequence/list of nodes."""
        for item in node:
            yield from self.visit(item)

    # STATEMENTS

    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> Symbols:
        """Visit a function definition in the following order:
            Decorators; Return annotation; Arguments default values;
            Remove name from context; Arguments names; Function body.
        """
        yield from self.visit_sequence(node.decorator_list)
        yield from self.visit_optional(node.returns)
        yield from self.visit_sequence(node.args.kw_defaults)
        yield from self.visit_sequence(node.args.defaults)
        self._scopes[node.name] = None
        with self.scope():
            yield from self.visit_sequence(node.args.kwonlyargs)
            yield from self.visit_sequence(node.args.args)
            yield from self.visit_optional(node.args.kwarg)
            yield from self.visit_optional(node.args.vararg)
            yield from self.visit_sequence(node.body)

    def visit_ClassDef(self, node: ClassDef) -> Symbols:
        """Visit in the following order:
            Decorators; Base classes; Keywords; Remove name from context; Body.
        """
        yield from self.visit_sequence(node.decorator_list)
        yield from self.visit_sequence(node.bases)
        yield from self.visit_sequence(node.keywords)
        self._scopes[node.name] = None
        with self.scope():
            yield from self.visit_sequence(node.body)

    def visit_FunctionDef(self, node: FunctionDef) -> Symbols:
        """Visit a function definition in the following order:
            Decorators; Return annotation; Arguments default values;
            Remove name from context; Arguments names; Function body.
        """
        yield from self.visit_sequence(node.decorator_list)
        yield from self.visit_optional(node.returns)
        yield from self.visit_sequence(node.args.kw_defaults)
        yield from self.visit_sequence(node.args.defaults)
        self._scopes[node.name] = None
        with self.scope():
            yield from self.visit_sequence(node.args.kwonlyargs)
            yield from self.visit_sequence(node.args.args)
            yield from self.visit_optional(node.args.kwarg)
            yield from self.visit_optional(node.args.vararg)
            yield from self.visit_sequence(node.body)

    def visit_Import(self, node: Import) -> Symbols:
        """Add the module to the current context."""
        for alias in node.names:
            self._scopes[alias.asname or alias.name] = alias.name
            yield (alias.name, node)

    def visit_ImportFrom(self, node: ImportFrom) -> Symbols:
        """Add the symbols to the current context."""
        for alias in node.names:
            module = node.module or ""
            qualified = f"{module}.{alias.name}"
            self._scopes[alias.asname or alias.name] = qualified
            yield (qualified, node)

    # EXPRESSIONS

    def visit_Attribute(self, node: Attribute) -> Symbols:
        """Postfix the seen symbols."""
        for lhs, _ in self.visit(node.value):
            yield (f"{lhs}.{node.attr}", node)

    def visit_Name(self, node: Name) -> Symbols:
        """If the symbol is getting overwritten, then delete it from the
        context, else yield it if it's known in this context.
        """
        if isinstance(node.ctx, (Del, Param, Store)):
            self._scopes[node.id] = None
        name = self._scopes.get(node.id)
        if name is not None:
            yield (name, node)


class WarnSymbols:
    """The flake8 plugin itself."""
    BANNED: Dict[str, str] = {}

    # The name and version class variables are required by flake8. It also
    # requires add_options and parse_options for options handling.

    name: str = "warn-symbols"
    version: str = __version__

    def __init__(self, tree: AST) -> None:
        self._tree = tree

    @classmethod
    def add_options(cls, parser: Any) -> None:
        """Register the --warn-symbols options on parser."""
        parser.add_option("--warn-symbols", default="", parse_from_config=True)

    # The following method might seem unsafe, but flake8 is designed this way:
    # The class hold its configuration, and it's the same for every checked
    # files.

    @classmethod
    def parse_options(cls, options: Any) -> None:
        """Load the obsolete symbols into cls.symbols."""
        lines = options.warn_symbols.splitlines()
        for line in lines:
            symbol, _, warning = line.partition("=")
            cls.BANNED[symbol.strip()] = warning.strip()

    def run(self) -> Iterator[FlakeError]:
        """Run the plugin."""
        visitor = QualifiedNamesVisitor()
        for symbol, node in visitor.visit(self._tree):
            # Get the warning associated to the most specific module name.
            warning: Optional[str] = None
            for module in submodules(symbol):
                warning = self.BANNED.get(module, warning)
            # If there's no associated warning, it means the symbol is not
            # deprecated.
            if warning is None:
                continue
            # Otherwise, we yield an error.
            yield (node.lineno, node.col_offset, f"B1 {warning}", type(self))


def submodules(symbol: str) -> Iterator[str]:
    """submodules("a.b.c") yields "a", then "a.b", then "a.b.c"."""
    bits = symbol.split(".")
    for i in range(len(bits)):
        yield ".".join(bits[:i+1])
