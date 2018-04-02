"""Flake8 plugin emitting warning for obsolete symbols."""

import builtins

from ast import (
    # Generic AST type
    AST,
    # Statements
    AsyncFunctionDef, ClassDef, FunctionDef, Import, ImportFrom,
    # Expressions
    Attribute, Name,
    # Expression context
    Del, Param, Store,
    # Visitors
    NodeVisitor, iter_child_nodes
)

from collections import ChainMap
from contextlib import contextmanager
from typing import Any, Iterator, MutableMapping, Optional, Sequence, Tuple


# TODO(AD): Good use of a custom type to document/clarify the code. Why all uppercase tho? Let's switch to normal case (like the other types/classes - AST is in my opinion poorly named) as initally i thought this was a constant when seeing it in other parts of the code (like SYMBOLS = 1)
SYMBOLS = Iterator[Tuple[str, AST]]


class QualifiedNamesVisitor(NodeVisitor):
    """QualifiedNamesVisitor.visit yields a pair (qualified_name, node) for all
    qualified names it finds in the given AST.

    It can handle:
        - Imports: Importing an obsolete symbol will yield it;
        - Delete statements: (del obsolete_symbol; obsolete symbol) doesn't
          yields anything;
        - Scopes: If you overwrite a symbol in a given function or class scope,
          it will not be overwriten in outer scopes;
        - Type annotations can yield.

    We don't support global and nonlocal statements for now, and the assignment
    operator untrack the symbol if it's on the left hand side, no matter what's
    on the right hand side.
    """
    def __init__(self) -> None:
        # TODO(AD): These 2 lines are difficult to understand (there is too much going on in 2 lines) - can you simplify and add a comment? What is it doing and why? What is context?
        init = dir(builtins)
        self._context = ChainMap(dict(zip(init, init)))

    # TODO(AD): Explain what this context manager does - or is it a flake8 thing?
    @contextmanager
    def scope(self) -> Iterator[MutableMapping[str, Any]]:
        self._context = self._context.new_child()
        try:
            yield self._context.maps[0]
        finally:
            self._context = self._context.parents

    def generic_visit(self, node: AST) -> SYMBOLS:
        for child in iter_child_nodes(node):
            yield from self.visit(child)

    # SPECIAL

    def visit_arg(self, node: AST) -> SYMBOLS:
        yield from self.visit_optional(node.annotation)
        self._context[node.arg] = None

    def visit_optional(self, node: Optional[AST]) -> SYMBOLS:
        if node is not None:
            yield from self.visit(node)

    def visit_list(self, node: Sequence[AST]) -> SYMBOLS:
        for item in node:
            yield from self.visit(item)

    # STATEMENTS

    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> SYMBOLS:
        yield from self.visit_list(node.decorator_list)
        yield from self.visit_optional(node.returns)
        yield from self.visit_list(node.args.kw_defaults)
        yield from self.visit_list(node.args.defaults)
        self._context[node.name] = None
        with self.scope():
            yield from self.visit(node.args)
            yield from self.visit_list(node.args.kwonlyargs)
            yield from self.visit_list(node.args.args)
            yield from self.visit_optional(node.args.kwarg)
            yield from self.visit_optional(node.args.vararg)
            yield from self.visit_list(node.body)

    def visit_ClassDef(self, node: ClassDef) -> SYMBOLS:
        yield from self.visit_list(node.decorator_list)
        yield from self.visit_list(node.bases)
        yield from self.visit_list(node.keywords)
        self._context[node.name] = None
        with self.scope():
            yield from self.visit_list(node.body)

    def visit_FunctionDef(self, node: FunctionDef) -> SYMBOLS:
        yield from self.visit_list(node.decorator_list)
        yield from self.visit_optional(node.returns)
        yield from self.visit_list(node.args.kw_defaults)
        yield from self.visit_list(node.args.defaults)
        self._context[node.name] = None
        with self.scope():
            yield from self.visit(node.args)
            yield from self.visit_list(node.args.kwonlyargs)
            yield from self.visit_list(node.args.args)
            yield from self.visit_optional(node.args.kwarg)
            yield from self.visit_optional(node.args.vararg)
            yield from self.visit_list(node.body)

    def visit_Import(self, node: Import) -> SYMBOLS:
        for alias in node.names:
            self._context[alias.asname or alias.name] = alias.name
            yield (alias.name, node)

    def visit_ImportFrom(self, node: ImportFrom) -> SYMBOLS:
        for alias in node.names:
            module = node.module or ""
            qualified = f"{module}.{alias.name}"
            self._context[alias.asname or alias.name] = qualified
            yield (qualified, node)

    # EXPRESSIONS

    def visit_Attribute(self, node: Attribute) -> SYMBOLS:
        for expr, _ in self.visit(node.value):
            yield (f"{expr}.{node.attr}", node)

    def visit_Name(self, node: Name) -> SYMBOLS:
        if isinstance(node.ctx, (Del, Param, Store)):
            self._context[node.id] = None
        name = self._context.get(node.id)
        if name is not None:
            yield (name, node)


class WarnSymbols:
    """The flake8 plugin itself."""
    name = "warn-symbols"
    # TODO(AD): This version number is likely to get out of sync with the one in setup.cfg. Can you make them one? It is good practice to put the module's version number in module/__init__.py as __version__
    # TODO(AD): Also for hardcoded attributes we use names all uppercase (like SYMBOLS)
    version = "0.0.1"
    symbols = {}

    def __init__(self, tree: AST) -> None:
        self._tree = tree

    @classmethod
    def add_options(cls, parser: Any) -> None:
        """Register the --warn-symbols options on parser."""
        parser.add_option("--warn-symbols", default="", parse_from_config=True)

    @classmethod
    def parse_options(cls, options: Any) -> None:
        """Load the obsolete symbols into cls.symbols."""
        lines = options.warn_symbols.splitlines()
        for line in lines:
            symbol, _, warning = line.partition("=")
            # TODO(AD): Is this interface required by flake8? Putting and changing stuff in a class attribute (cls.symbol) seems dangerous as it is not safe if multiple callers call parse_options(). Is this something that could happen? If not (or if it is how flake8 wants plugins to be designed) please add a comment explaining why. If it can happen and flake8 allows this, i think the symbols to check for should be an instance attribute instead of a class attribute (it would work like this here: return cls(symbols)), but I don't know how flake8 plugins work :)
            cls.symbols[symbol.strip()] = warning.strip()

    def run(self) -> Iterator[Tuple[int, int, str, type]]:
        """Run the plugin."""
        # TODO(AD): Add comments for each major step of this method
        visitor = QualifiedNamesVisitor()
        for symbol, node in visitor.visit(self._tree):
            message = None
            for module in submodules(symbol):
                # TODO(AD): Let's rename message to error_message (I was confused for a minute)
                message = self.symbols.get(module, message)
            if message is None:
                continue
            yield (node.lineno, node.col_offset, f"B1 {message}", type(self))


# TODO(AD): Yielding here seems overkill; not a big deal but it makes the code slightly harder to read - let's just return a list?
def submodules(symbol: str) -> Iterator[str]:
    """submodules("a.b.c") -> a, a.b, a.b.c"""
    bits = symbol.split(".")
    for i in range(len(bits)):
        yield ".".join(bits[:i+1])
