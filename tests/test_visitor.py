"""Test for SymbolsVisitor. The tests are in the form of a sequence of tuples
of (line, expectation) where line is a line of code and expectation is a
collection of symbols we expect to encounter in the former.

The tests are grouped together into TESTS and evaluated by test_visitor.
"""

from ast import parse
from typing import Collection, Sequence, Tuple

from alfred import SymbolsVisitor


T = Sequence[Tuple[str, Collection[str]]]

TEST_ALIAS: T = (
    ("import a as b       ", ("a",)),
    ("from a import b as c", ("a.b",)),
    ("b                   ", ("a",)),
    ("c                   ", ("a.b",))
)

TEST_ANNOTATIONS: T = (
    ("import a             ", ("a",)),
    ("from b import T      ", ("b.T",)),
    ("x: a.T = 1           ", ("a.T",)),
    ("def a(T: T = 1) -> a:", ("b.T", "a")),
    ("    pass             ", ())
)

TEST_COMPREHENSION: T = (
    ("import a                  ", ("a",)),
    ("import b                  ", ("b",)),
    ("[a for a in range(2) if a]", ("range",)),
    ("a                         ", ("a",)),
    ("{a for a in range(2) if a}", ("range",)),
    ("a                         ", ("a",)),
    ("(a for a in range(2) if a)", ("range",)),
    ("a                         ", ("a",)),
    ("{a:b for a, b in it}      ", ()),
    ("a, b                      ", ("a", "b"))
)

TEST_DELETE: T = (
    ("from a import b", ("a.b",)),
    ("del b          ", ()),
    ("b              ", ())
)

TEST_EXCEPT: T = (
    ("from a import b        ", ("a.b",)),
    ("try:                   ", ()),
    ("    raise ValueError() ", ("ValueError",)),
    ("except ValueError as b:", ("ValueError",)),
    ("    pass               ", ()),
    ("b                      ", ())
)

TEST_HEADER: T = (
    ("import a, b, c, d", ("a", "b", "c", "d")),
    ("def a(b: c = d): ", ("c", "d",)),
    ("    a, b, c, d   ", ("c", "d",)),
    ("a, b, c, d       ", ("b", "c", "d"))
)

TEST_IMPORT: T = (
    ("import a       ", ("a",)),
    ("import a       ", ("a",)),
    ("from a import b", ("a.b",)),
    ("from c import d", ("c.d",)),
    ("from d import b", ("d.b",)),
    ("import a       ", ("a",)),
    ("from a import b", ("a.b",)),
)

TEST_LAMBDA: T = (
    ("import a     ", ("a",)),
    ("import b     ", ("b",)),
    ("lambda a: a  ", ()),
    ("a            ", ("a",)),
    ("lambda b=a: b", ("a",)),
    ("a            ", ("a",)),
    ("lambda b=a: b", ("a",)),
    ("a, b         ", ("a", "b"))
)

TEST_OVERWRITE: T = (
    ("from m import a, b, c, d", ("m.a", "m.b", "m.c", "m.d")),
    ("a, b, c, d              ", ("m.a", "m.b", "m.c", "m.d")),
    ("a = 1                   ", ()),
    ("a, b, c, d              ", ("m.b", "m.c", "m.d")),
    ("def b(c: d):            ", ("m.d",)),
    ("    a, b, c, d          ", ("m.d",)),
    ("class c:                ", ()),
    ("    a = d               ", ("m.d",))
)

TESTS: Collection[T] = (
    TEST_ALIAS,
    TEST_ANNOTATIONS,
    TEST_COMPREHENSION,
    TEST_DELETE,
    TEST_EXCEPT,
    TEST_HEADER,
    TEST_IMPORT,
    TEST_LAMBDA,
    TEST_OVERWRITE,
)


def test_visitor() -> None:
    """Build an AST from the tests in TESTS, compare the actual output with
    the expected output.
    """
    for test in TESTS:
        # Transpose test. We now have a sequence of code lines, and another for
        # expected symbols on a given line.
        lines, symset = zip(*test)

        # Concat the code lines, separating them by a newline, and visit the
        # resulting code.
        parsed = parse("\n".join(lines))
        results = SymbolsVisitor().visit(parsed)

        # Build a set of (line, expected symbols) from symset.
        # symbols is the actual output.
        expect = {(l+1, n) for l, s in enumerate(symset) for n in s}
        symbols = {(node.lineno, name) for name, node in results}

        assert symbols == expect
