import collections
import itertools
import os

import numpy as np
from mathics.core.builtin import Builtin
from mathics.core.load_builtin import add_builtins

import core
import layout as lt
import ui
import render
import sym
import util

#
# Manipulate builtin
#

class Manipulate(Builtin):

    attributes = core.A_HOLD_FIRST

    # TODO: expr is held so it arrives here safely, but for some reason by the time it
    # gets to eval_makeboxes it has some funky HoldForm's interspersed. To see that,
    # comment this eval out and look at the expr in eval_makeboxes. Don't know why or how to avoid.
    # So hack: immediately turn it into a String, then re-parse in eval_makeboxes.
    # There must be a better way.
    def eval(self, evaluation, expr, sliders):
        "Manipulate[expr_, sliders___]"
        if not isinstance(expr, core.String):
            return core.Expression(sym.SymbolManipulate, core.String(str(expr)), sliders)
        return None

    def eval_makeboxes(self, evaluation, expr, sliders, form, *args, **kwargs):
        "MakeBoxes[Manipulate[expr_, sliders___], form:StandardForm|TraditionalForm|OutputForm|InputForm]"
        expr = evaluation.parse(expr.value) # hack - see note above
        return ManipulateBox(expr, sliders)


    """
    options = {
        "Axes": "{False, True}",
        "AspectRatio": "1 / GoldenRatio",
    }
    """

# TODO: Mathematica does something more complicated, and more general,
# involving DynamicModule, Dymanic, Dynamic*Box, etc.
# Do we want to emulate that?
class ManipulateBox(core.BoxExpression):
    def __init__(self, expr, sliders):
        super().__init__(self, expr, sliders)

# regarding expression=False: see mathics/core/builtin.py:221 "can be confusing"
add_builtins([("System`Manipulate", Manipulate(expression=False))])


#
# given a ManipulateBox Expression, compute a layout
#

def layout_ManipulateBox(fe, manipulate_expr, layout_options):

    target_expr = manipulate_expr.elements[0]
    slider_expr = manipulate_expr.elements[1]

    # TODO: slider_expr came from matching an ___ pattern in Manipulate (see above)
    # According to Mathematica documentation(?), the ___ notation is meant to take
    # the rest of elements and wrap them in a List, even if there is only one.
    # Instead we get just the element if only one, and the elements in a Sequence (not List) if >1
    # Am I doing something wrong or misunderstanding?
    if slider_expr.head == sym.SymbolSequence:
        slider_specs = [s.to_python() for s in slider_expr.elements]
    else:
        slider_specs = [slider_expr.to_python()]

    # parse slider specs
    S = collections.namedtuple("S", ["name", "lo", "init", "hi", "step"])
    def slider(spec):
        v, lo, hi = spec[0:3]
        step = spec[3] if len(spec) > 3 else (hi-lo)/10 # TODO: better default step
        v, init = v if isinstance(v, (list,tuple)) else (v, lo)
        v = str(v).split("`")[-1] # strip off namespace pfx
        spec = S(v, lo, init, hi, step)
        return spec
    sliders = [slider(spec) for spec in slider_specs]

    # compute a layout for an expr given a set of values
    # this is the callback for this Manipulate to update the target with new values
    def eval_and_layout(values):
        # TODO: always Global?
        # TODO: always Real?
        # TODO: best order for replace_vars and eval?
        values = {s.name: a for s, a in zip(sliders, values)}
        with util.Timer("replace and eval"):
            expr = target_expr.replace_vars({"Global`"+n: core.Real(v) for n, v in values.items()})
            expr = expr.evaluate(fe.session.evaluation)
        with util.Timer("layout"):
            layout = lt.expression_to_layout(fe, expr)
        return layout

    # compute the layout for the plot
    init_values = [s.init for s in sliders]
    init_target_layout = eval_and_layout(init_values)
    layout = ui.manipulate(init_target_layout, sliders, eval_and_layout)
        
    return layout



