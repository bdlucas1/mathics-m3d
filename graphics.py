"""
Layout functions for GraphicsBox, Graphics3DBox, and ManipulateBox.
These functions are called by expression_to_layout in layout.py; see
comment there for general explanation of layouts.
"""

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
from consumer import GraphicsConsumer


def layout_GraphicsBox(dim, fe, expr, layout_options):

    graphics = GraphicsConsumer(fe, expr, layout_options)

    builder = render.FigureBuilder(dim, fe, graphics.options)

    switch = {
        sym.SymbolPolygon: builder.add_polys,
        sym.SymbolLine: builder.add_lines,
        sym.SymbolPoint: builder.add_points,
        sym.SymbolRectangle: builder.add_rectangles,
        sym.SymbolDisk: builder.add_disks,
        sym.SymbolRGBColor: builder.set_color_rgb,
    }

    for item in graphics.items():
        switch[item[0]](*item[1:])

    figure = builder.figure()
    layout = ui.graph(figure, graphics.options.image_size[1])
    return layout

#
#
#

from manipulate import layout_ManipulateBox

layout_funs = {
    sym.SymbolManipulateBox: layout_ManipulateBox,
    sym.SymbolGraphicsBox: lambda *args: layout_GraphicsBox(2, *args),
    sym.SymbolGraphics3DBox: lambda *args: layout_GraphicsBox(3, *args)
}


