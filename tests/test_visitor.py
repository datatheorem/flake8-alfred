from ast import parse
from typing import Collection, Sequence, Tuple

from willie import QualifiedNamesVisitor


T = Sequence[Tuple[str, Collection[str]]]

TEST_ANNOTATIONS: T = (
    ("import a               ", ("a",)),
    ("from b import T        ", ("b.T",)),
    ("x: a.T = 1             ", ("a.T",)),
    ("def f(a: a.T = 1) -> a:", ("a", "a.T")),
    ("    pass               ", ()),
    ("def T(T: T = 1) -> T:  ", ("b.T",)),
    ("    pass               ", ())
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
    TEST_ANNOTATIONS, TEST_SCOPES
)


def test_visitor():
    for test in TESTS:
        lines, symset = zip(*test)

        parsed = parse("\n".join(lines))
        results = QualifiedNamesVisitor().visit(parsed)

        expect = {(l+1, n) for l, s in enumerate(symset) for n in s}
        symbols = {(node.lineno, name) for name, node in results}

        assert symbols == expect
