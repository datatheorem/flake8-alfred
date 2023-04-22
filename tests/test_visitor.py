"""Test for SymbolsVisitor. The tests are in the form of a sequence of tuples
of (line, expectation) where line is a line of code and expectation is a
collection of symbols we expect to encounter in the former.
"""

from ast import parse
from collections.abc import Collection
from collections.abc import Sequence

from pytest import mark

from flake8_alfred import SymbolsVisitor


TEST_ALIAS = (
    ("import a as b       ", ("a",)),
    ("from a import b as c", ("a.b",)),
    ("b                   ", ("a",)),
    ("c                   ", ("a.b",))
)

TEST_ANNOTATIONS = (
    ("import a             ", ("a",)),
    ("from b import T      ", ("b.T",)),
    ("x: a.T = 1           ", ("a.T",)),
    ("def a(T: T = 1) -> a:", ("b.T", "a")),
    ("    pass             ", ())
)

TEST_COMPREHENSION = (
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

TEST_DELETE = (
    ("from a import b", ("a.b",)),
    ("del b          ", ()),
    ("b              ", ())
)

TEST_EXCEPT = (
    ("from a import b        ", ("a.b",)),
    ("try:                   ", ()),
    ("    raise ValueError() ", ("ValueError",)),
    ("except ValueError as b:", ("ValueError",)),
    ("    pass               ", ()),
    ("b                      ", ())
)

TEST_HEADER = (
    ("import a, b, c, d", ("a", "b", "c", "d")),
    ("def a(b: c = d): ", ("c", "d",)),
    ("    a, b, c, d   ", ("c", "d",)),
    ("a, b, c, d       ", ("b", "c", "d"))
)

TEST_IMPORT = (
    ("import a       ", ("a",)),
    ("import a       ", ("a",)),
    ("from a import b", ("a.b",)),
    ("from c import d", ("c.d",)),
    ("from d import b", ("d.b",)),
    ("import a       ", ("a",)),
    ("from a import b", ("a.b",)),
)

TEST_LAMBDA = (
    ("import a     ", ("a",)),
    ("import b     ", ("b",)),
    ("lambda a: a  ", ()),
    ("a            ", ("a",)),
    ("lambda b=a: b", ("a",)),
    ("a            ", ("a",)),
    ("lambda b=a: b", ("a",)),
    ("a, b         ", ("a", "b"))
)

TEST_OVERWRITE = (
    ("from m import a, b, c, d", ("m.a", "m.b", "m.c", "m.d")),
    ("a, b, c, d              ", ("m.a", "m.b", "m.c", "m.d")),
    ("a = 1                   ", ()),
    ("a, b, c, d              ", ("m.b", "m.c", "m.d")),
    ("def b(c: d):            ", ("m.d",)),
    ("    a, b, c, d          ", ("m.d",)),
    ("class c:                ", ()),
    ("    a = d               ", ("m.d",))
)


@mark.parametrize(
    "test",
    (
        TEST_ALIAS,
        TEST_ANNOTATIONS,
        TEST_COMPREHENSION,
        TEST_DELETE,
        TEST_EXCEPT,
        TEST_HEADER,
        TEST_IMPORT,
        TEST_LAMBDA,
        TEST_OVERWRITE,
    ),
)
def test_visitor(test: Sequence[tuple[str, Collection[str]]]) -> None:
    """Build an AST from the tests in TESTS, compare the actual output with
    the expected output.
    """
    # Transpose test. We now have a sequence of code lines, and another for
    # expected symbols on a given line.
    lines, symset = zip(*test)

    # Concat the code lines, separating them by a newline, and visit the
    # resulting code.
    parsed = parse("\n".join(lines))
    results = SymbolsVisitor().visit(parsed)

    # Build a set of (line, expected symbols) from symset.
    # symbols is the actual output.
    expect = {(line + 1, n) for line, s in enumerate(symset) for n in s}
    symbols = {(node.lineno, name) for name, node in results}

    assert symbols == expect
