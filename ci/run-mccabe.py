""" Tiny wrapper for mccabe module.

Iterate over all the python sources, and print results in
an easily parseable format

If you are already using pyflakes or prospector, you won't need this :)

"""

import ast
import sys

import mccabe
from path import Path


def ignore(py_source):
    parts = py_source.splitall()
    # Ignore 'hidden' files
    if any(x.startswith(".") for x in parts):
        return True
    return False


def yield_sources():
    top = Path(".")
    for py_source in top.walkfiles("*.py"):
        py_source = py_source.relpath(top)
        if not ignore(py_source):
            yield py_source


def process(py_source, max_complexity):
    res = list()
    code = py_source.text()
    tree = compile(code, py_source, "exec", ast.PyCF_ONLY_AST)
    visitor = mccabe.PathGraphingAstVisitor()
    visitor.preorder(tree, visitor)
    for graph in visitor.graphs.values():
        if graph.complexity() > max_complexity:
            res.append((py_source, graph))
    return res


def main():
    max_complexity = int(sys.argv[1])
    complex_code = list()
    for py_source in yield_sources():
        res = process(py_source, max_complexity)
        complex_code.extend(res)
    if not complex_code:
        return
    print("Some part of the code are above the maximum allowed complexity")
    print("Here's the list of functions or methods you should refactor:")
    for (source, graph) in complex_code:
        text = "{}:{} {} ({}/{})"
        text = text.format(source, graph.lineno, graph.entity, graph.complexity(), max_complexity)
        print(text)
    sys.exit(1)


if __name__ == "__main__":
        main()
