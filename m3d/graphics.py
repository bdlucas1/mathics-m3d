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

from m3d import core, sym, util
import m3d.layout
import m3d.ui
import m3d.render

from m3d.consumer import GraphicsConsumer


def layout_GraphicsBox(dim, fe, expr, layout_options):

    graphics = GraphicsConsumer(fe, expr, layout_options)

    builder = m3d.render.FigureBuilder(dim, fe, graphics.options)

    switch = {
        sym.SymbolPolygon: builder.add_polys,
        sym.SymbolLine: builder.add_lines,
        sym.SymbolPoint: builder.add_points,
        sym.SymbolRectangle: builder.add_rectangles,
        sym.SymbolDisk: builder.add_disks,
        sym.SymbolInset: builder.add_insets,
        sym.SymbolStyle: builder.set_style,
        sym.SymbolRGBColor: builder.set_color_rgb,
        sym.SymbolAbsoluteThickness: builder.set_thickness,
    }

    for item in graphics.items():
        switch[item[0]](*item[1:])

    figure, height = builder.figure()
    layout = m3d.ui.graph(figure, height)
    return layout

#
#
#

from m3d.manipulate import layout_ManipulateBox

layout_funs = {
    sym.SymbolManipulateBox: layout_ManipulateBox,
    sym.SymbolGraphicsBox: lambda *args: layout_GraphicsBox(2, *args),
    sym.SymbolGraphics3DBox: lambda *args: layout_GraphicsBox(3, *args)
}


