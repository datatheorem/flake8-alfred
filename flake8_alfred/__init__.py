"""Flake8 plugin emitting warning for banned symbols."""

__all__ = ["SymbolsVisitor", "WarnSymbols"]

from ast import AST
from typing import Any, Dict, Iterator, Optional, Tuple

from pkg_resources import get_distribution
from .symbols import SymbolsVisitor


# Flake8 error type: (line number, column, warning message, caller type)
FlakeError = Tuple[int, int, str, type]


class WarnSymbols:
    """The flake8 plugin itself."""
    BANNED: Dict[str, str] = {}

    # The name and version class variables are required by flake8. It also
    # requires add_options and parse_options for options handling.

    name: str = "warn-symbols"
    version: str = get_distribution("flake8-alfred").version

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
        """Load the banned symbols into cls.BANNED."""
        lines = options.warn_symbols.splitlines()
        for line in lines:
            symbol, _, warning = line.partition("=")
            cls.BANNED[symbol.strip()] = warning.strip()
        cls.BANNED.pop("", None)

    def run(self) -> Iterator[FlakeError]:
        """Run the plugin."""
        visitor = SymbolsVisitor()
        for symbol, node in visitor.visit(self._tree):
            # Get the warning associated to the most specific module name.
            warning: Optional[str] = None
            for module in submodules(symbol):
                warning = self.BANNED.get(module, warning)
            # If there's no associated warning, it means the symbol is valid.
            if warning is None:
                continue
            # Otherwise, we yield an error.
            yield (node.lineno, node.col_offset, f"B1 {warning}", type(self))


def submodules(symbol: str) -> Iterator[str]:
    """submodules("a.b.c") yields "a", then "a.b", then "a.b.c"."""
    bits = symbol.split(".")
    for i in range(len(bits)):
        yield ".".join(bits[:i+1])
