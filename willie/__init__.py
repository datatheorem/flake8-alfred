from ast import Del, NodeVisitor, Store, iter_child_nodes
from collections import ChainMap
from contextlib import contextmanager
from itertools import chain


def submodules(module_name: str):
    bits = module_name.split(".")
    for i in range(1, len(bits)):
        yield ".".join(bits[:i])


class QualifiedNamesVisitor(NodeVisitor):
    def __init__(self):
        self._context = ChainMap()

    @contextmanager
    def block(self, **kwargs):
        self._context = self._context.new_child(kwargs)
        try:
            yield kwargs
        finally:
            self._context = self._context.parents

    def generic_visit(self, node):
        for i in iter_child_nodes(node):
            yield from self.visit(i)

    # STATEMENTS

    def visit_AsyncFunctionDef(self, node):
        self._context[node.name] = None
        for decorator in node.decorator_list:
            yield from self.visit(decorator)
        with self.block():
            yield from self.visit(node.args)
            for item in node.body:
                yield from self.visit(statement)

    def visit_ClassDef(self, node):
        self._context.pop(node.name, None)
        for decorator in node.decorator_list:
            yield from self.visit(decorator)
        with self.block():
            for expr in chain(node.bases, node.keywords):
                yield from self.visit(expr)
            for statement in node.body:
                yield from self.visit(statement)

    def visit_FunctionDef(self, node):
        self._context[node.name] = None
        for decorator in node.decorator_list:
            yield from self.visit(decorator)
        with self.block():
            yield from self.visit(node.args)
            for statement in node.body:
                yield from self.visit(statement)

    def visit_Import(self, node):
        for alias in node.names:
            self._context[alias.asname or alias.name] = alias.name
            for module in submodules(alias.name):
                yield (module, node)

    def visit_ImportFrom(self, node):
        new = {s.asname or s.name: f"{node.module}.{s.name}" for s in node.names}
        self._context.update(new)
        if node.module is not None:
            for module in submodules(node.module):
                yield (module, node)
        for item in new.values():
            yield (item, node)

    # EXPRESSIONS

    def visit_Attribute(self, node):
        children = list(self.visit(node.value))
        yield from children
        yield from ((f"{item}.{node.attr}", node) for item, _ in children)

    def visit_Name(self, node):
        if isinstance(node.ctx, (Del, Store)):
            self._context[node.id] = None
        name = self._context.get(node.id)
        if name is not None:
            yield (name, node)


class BanSymbolPlugin:
    name = "ban-symbol"
    version = "0.0.1"
    banned = {}

    def __init__(self, tree):
        self._tree = tree

    @classmethod
    def add_options(cls, parser):
        parser.add_option("--banned-symbols", default="", parse_from_config=True)

    @classmethod
    def parse_options(cls, options):
        lines = options.banned_symbols.splitlines()
        for line in lines:
            symbol, _, warning = line.partition("=")
            cls.banned[symbol.strip()] = warning.strip()

    def run(self):
        visitor = QualifiedNamesVisitor()
        for symbol, node in visitor.visit(self._tree):
            try:
                message = self.banned[symbol]
            except KeyError:
                continue
            yield (node.lineno, node.col_offset, f"B1 {message}", type(self))
