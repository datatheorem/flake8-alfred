from ast import parse
from typing import Collection, Sequence, Tuple

from alfred import SymbolsVisitor


T = Sequence[Tuple[str, Collection[str]]]

TEST_ANNOTATIONS: T = (
    ("import a             ", ("a",)),
    ("from b import T      ", ("b.T",)),
    ("x: a.T = 1           ", ("a.T",)),
    ("def a(T: T = 1) -> a:", ("b.T", "a")),
    ("    pass             ", ())
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
    ("from a import b ", ("a.b",)),
    ("def b(b: b = b):", ("a.b",)),
    ("    pass        ", ()),
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

TEST_SCOPES: T = (
    ("import a          ", ("a",)),
    ("from a import b   ", ("a.b",)),
    ("from b import c   ", ("b.c",)),
    ("from c import d   ", ("c.d",)),
    ("del d             ", ()),
    ("def f(x=b, a=a.c):", ("a.b", "a.c")),
    ("    _ = a.b       ", ()),
    ("    a = 22        ", ()),
    ("    c = a         ", ()),
    ("    def c():      ", ()),
    ("        a = 1     ", ()),
    ("        del a     ", ()),
    ("a.b               ", ("a.b",))
)

TESTS: Collection[T] = (
    TEST_ANNOTATIONS,
    TEST_DELETE,
    TEST_EXCEPT,
    TEST_HEADER,
    TEST_IMPORT,
    TEST_OVERWRITE,
    TEST_SCOPES
)


def test_visitor():
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