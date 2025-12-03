import collections
import os
from typing import Optional

import numpy as np

import core
import sym

import util

#
# traverse a Graphics or Graphics3D expression and collect points, lines, and triangles
# as numpy arrays that are efficient to traverse
#
# TODO: can this be plugged into existing machinery for processing Graphics and Graphics3D?
# there seems to be a bunch of stuff related to this in mathics.format that could be reused,
# but it currently seems to assume that a string is being generated to be saved in a file
#


# where possible things are converted to np.ndarray
#   (not possible e.g. in lists of items, which may be non-homogeneous)
# indexes are converted from 1-based to 0-based TODO not yet
# where possible, lists of items are coalesced by kind

Waiting = collections.namedtuple("Waiting", ["kind", "vertices", "items", "colors"])

class GraphicsOptions:

    def __init__(self, dim, fe, expr, layout_options):

        graphics_options = expr.get_option_values(expr.elements[1:])

        # gets option "name", converting to python
        # System`Automatic is converted to None (TODO: ok?)
        # expands to a list of size want_list if requested
        def get_option(name, want_list=None):
            x = graphics_options[name].to_python()
            auto = lambda x: None if x=="System`Automatic" else x
            if want_list:
                if not isinstance(x, (list,tuple)):
                    x = [x] * want_list
                x.extend([None] * (want_list - len(x)))
                x = [auto(xx) for xx in x]
            else:
                x = auto(x)
            #print(name, x)
            return x

        # NEXT
        #boxed
        #axes
        #background
        #axes_style
        #label_style
        #plot_range_padding
        #tick_style
        #if dim==3:
        #    box_ratios
        #    view_point
        #    lighting
        # TBD: add showscale, colorscale, boxed
        # TBD: vertexcolors, colorscale, hue, etc.

        # Axes
        self.axes = get_option("System`Axes", 3)

        # Frame
        self.frame = get_option("System`Frame")

        # ImageSize, AspectRatio
        # TODO: what if anyting to do with returned aspect?
        width, height, multi, aspect = expr._get_image_size(
            dict(layout_options), # copy because _get_image_size modifies
            graphics_options,
            None
        )
        # TODO: shouldn't this be done by _get_image_size?
        if not aspect:
            aspect = 1
        self.image_size = [width * multi, height * multi * aspect]
        
        # PlotRange
        self.plot_range = get_option("System`PlotRange", 3)

        if dim == 3:

            # Boxed
            self.boxed = get_option("System`Boxed")

            # BoxRatios
            self.box_ratios = get_option("System`BoxRatios")            

            # ViewPoint
            self.view_point = get_option("System`ViewPoint")

        # full set - comment out as implemented
        alignment_point = get_option("System`AlignmentPoint")
        aspect_ratio = get_option("System`AspectRatio")
        axes = get_option("System`Axes")
        axes_label = get_option("System`AxesLabel")
        axes_origin = get_option("System`AxesOrigin")
        axes_style = get_option("System`AxesStyle")
        background = get_option("System`Background")
        baseline_position = get_option("System`BaselinePosition")
        base_style = get_option("System`BaseStyle")
        content_selectable = get_option("System`ContentSelectable")
        coordinates_tool_options = get_option("System`CoordinatesToolOptions")
        epilog = get_option("System`Epilog")
        format_type = get_option("System`FormatType")
        #frame = get_option("System`Frame")
        frame_label = get_option("System`FrameLabel")
        frame_style = get_option("System`FrameStyle")
        frame_ticks = get_option("System`FrameTicks")
        frame_ticks_style = get_option("System`FrameTicksStyle")
        grid_lines = get_option("System`GridLines")
        grid_lines_style = get_option("System`GridLinesStyle")
        image_margins = get_option("System`ImageMargins")
        image_padding = get_option("System`ImagePadding")
        image_size = get_option("System`ImageSize")
        label_style = get_option("System`LabelStyle")
        method = get_option("System`Method")
        plot_label = get_option("System`PlotLabel")
        plot_range = get_option("System`PlotRange")
        plot_range_clipping = get_option("System`PlotRangeClipping")
        plot_range_padding = get_option("System`PlotRangePadding")
        plot_region = get_option("System`PlotRegion")
        preserve_image_options = get_option("System`PreserveImageOptions")
        prolog = get_option("System`Prolog")
        rotate_label = get_option("System`RotateLabel")
        ticks = get_option("System`Ticks")
        ticks_style = get_option("System`TicksStyle")
        if dim == 3:
            face_grids_style = get_option("System`FaceGridsStyle")
            boxed = get_option("System`Boxed")
            view_center = get_option("System`ViewCenter")
            view_range = get_option("System`ViewRange")
            view_vertical = get_option("System`ViewVertical")
            touchscreen_auto_zoom = get_option("System`TouchscreenAutoZoom")
            view_vector = get_option("System`ViewVector")
            lighting = get_option("System`Lighting")
            view_matrix = get_option("System`ViewMatrix")
            view_projection = get_option("System`ViewProjection")
            clip_planes_style = get_option("System`ClipPlanesStyle")
            controller_linking = get_option("System`ControllerLinking")
            #view_point = get_option("System`ViewPoint")
            axes_edge = get_option("System`AxesEdge")
            rotation_action = get_option("System`RotationAction")
            #box_ratios = get_option("System`BoxRatios")
            controller_path = get_option("System`ControllerPath")
            box_style = get_option("System`BoxStyle")
            face_grids = get_option("System`FaceGrids")
            view_angle = get_option("System`ViewAngle")
            spherical_region = get_option("System`SphericalRegion")
            clip_planes = get_option("System`ClipPlanes")


        #for n, v in graphics_options.items(): print(n, v)
        #for n, v in self.__dict__.items(): print(n, v)

class GraphicsConsumer:

    # if None, we are not in a GraphicsComplex, and a coordinate is a list of xy[z]
    # if not None, we are in a GraphicsComplex, and a coordinate is an integer index into vertices
    vertices: Optional[list] = None

    # this coalesces consecutive items of the same kind
    waiting = None

    def __init__(self, fe, expr, layout_options):

        assert expr.head in (sym.SymbolGraphics, sym.SymbolGraphics3D, sym.SymbolGraphicsBox, sym.SymbolGraphics3DBox)

        self.dim = 3 if expr.head in (sym.SymbolGraphics3D, sym.SymbolGraphics3DBox) else 2
        self.fe = fe
        self.expr = expr
        self.vertices = None
        self.graphics = expr.elements[0]

        # TODO: these are not being passed through
        self.options = GraphicsOptions(self.dim, fe, expr, layout_options)
        self.options.showscale = False
        self.options.colorscale = "viridis"

    # TODO: still necessary?
    def process_array(self, array):
        if isinstance(array, core.NumericArray):
            return array.value
        else:
            raise ValueError(f"array type is {type(array)}")

    def find_vertex_colors(self, expr, wanted_depth):

        def to_rgb(colors):
            if colors is None:
                return
            extract = lambda color: tuple(c.to_python() for c in color.elements)
            extract = np.vectorize(extract)
            colors = np.array(extract(colors))
            colors = colors.transpose(1, 2, 0) # np.vectorize wonky behavior...
            #print("xxx after to_rgb colors", colors.shape)
            return colors
                
        for e in expr.elements[1:]:
            if e.head is sym.SymbolRule and e.elements[0] is sym.SymbolVertexColors:
                colors_expr = e.elements[1]
                if colors_expr.head == sym.SymbolRGBColor:
                    colors = colors_expr.elements[0]
                    if isinstance(colors, core.NumericArray):
                        #print(colors.value)
                        return colors.value
                elif colors_expr.head is sym.SymbolList:
                    colors = self.list_or_array(colors_expr, wanted_depth)
                    colors = np.array(colors)
                    with util.Timer("vertex colors to rgb"):
                        colors = np.array([to_rgb(np.array(c)) for c in colors])
                    return colors


    def list_or_array(self, expr, wanted_depth):

        if isinstance(expr, core.NumericArray):
            array = expr.value
        elif isinstance(expr, core.Expression):
            array = expr.to_python()

        # make array have the desired depth
        depth = lambda x: 1 + depth(x[0]) if isinstance(x, (list,tuple,np.ndarray)) else 0
        while depth(array) < wanted_depth:
            array = [array]

        # array must be homogeneous so we can make it an array
        array = [np.array(item) for item in array]

        return array


    def item(self, kind, expr, wanted_depth, colors):

        # item is specified either as a NumericArray or as a nest List
        items_wanted_depth = wanted_depth+1 if self.vertices is None else wanted_depth
        items = self.list_or_array(expr.elements[0], items_wanted_depth)

        # do we have VertexColors?
        local_colors = self.find_vertex_colors(expr, wanted_depth)
        if local_colors is not None:
            colors = local_colors
                
        # convert 1-based indexes to 0-based if in GraphicsComplex
        if self.vertices is not None:
            for item in items:
                item -= 1

        # flush if needed, add our items to waiting items
        if self.waiting is None:
            self.waiting = Waiting(kind, self.vertices, items, colors)
        # TODO: what about colors?
        elif self.waiting.kind == kind and self.waiting.vertices is self.vertices:
            self.waiting.items.extend(items)
        else:
            yield from self.flush()
            self.waiting = Waiting(kind, self.vertices, items, colors)

    def flush(self):
        """ Flush any waiting items """
        if self.waiting is not None:

            # stack items if possible for more efficent processing
            items, colors = self.waiting.items, self.waiting.colors
            try:
                items = [np.vstack(items)]
                colors = [np.vstack(colors)] if colors is not None else None
            except (ValueError, TypeError):
                shapes = np.array([item.shape for item in items])
                print(f"can't stack {len(items)} {self.waiting.kind} {shapes}")

            colors = colors if colors is not None else [None] * len(items)
            for item, color in zip(items, colors):
                #if color is not None: print("xxx yielding color", color.shape)
                yield self.waiting.kind, self.waiting.vertices, item, color

            self.waiting = None

    def process(self, expr, colors=None):

        def directives(ctx, expr):

            if color := core.expression_to_color(expr):
                rgba = color.to_rgba()
                yield (sym.SymbolRGBColor, rgba, ctx)

            elif expr.head == sym.SymbolEdgeForm:
                for e in expr.elements:
                    yield from directives("edge", e)

            elif expr.head == sym.SymbolRule:
                # handled elsewhere
                pass

            else:
                print(f"uknown graphics element {expr.head}")

        if expr.head == sym.SymbolList:
            for e in expr:
                yield from self.process(e)

        elif expr.head in (sym.SymbolGraphicsComplex, sym.SymbolGraphicsComplexBox):
            # TODO: allow elements for array
            self.vertices = self.process_array(expr.elements[0])
            colors = self.find_vertex_colors(expr, wanted_depth = 2)
            for e in expr.elements[1:]:
                yield from self.process(e, colors)
            self.vertices = None
            yield from self.flush()

        elif expr.head in (sym.SymbolPolygon, sym.SymbolPolygonBox, sym.SymbolPolygon3DBox):
            yield from self.item(sym.SymbolPolygon, expr, wanted_depth=3, colors=colors)
        elif expr.head in (sym.SymbolLine, sym.SymbolLineBox, sym.SymbolLine3DBox):
            yield from self.item(sym.SymbolLine, expr, wanted_depth=3, colors=colors)
        elif expr.head in (sym.SymbolPoint, sym.SymbolPointBox):
            yield from self.item(sym.SymbolPoint, expr, wanted_depth=2, colors=colors)

        else:
            yield from directives(None, expr)

    def items(self):

        # process the items
        yield from self.process(self.graphics)

        # flush anything still waiting
        yield from self.flush()

