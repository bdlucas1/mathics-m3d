import os

import core
import util

session = core.MathicsSession()

for fn in os.listdir("."):

    if fn.endswith(".m"):
        with open(fn, "r") as f:
            expr = f.read()
            expr = session.parse(expr)
            expr = expr.evaluate(session.evaluation)
            with open(fn + ".txt", "w") as g:
                util.print_expression_tree(expr, file=g)


