import numpy as np
import numpy.linalg as la
import plotly.graph_objects as go
import os
import re
import copy
import ticker

import mesh2d
import util


# TODO: move to consumer
# if vertices is none, that means items have the points at the leaves
# instead of indexes into the vertices. Reshape the arrays so that
# we have it in normalized form:
#     vertices are point coordinates
#     items have indexes into vertices list instead of the coordinates
#     colors are 1-1 with vertices
def need_vertices(vertices, items, colors):
    if vertices is None:
        with util.Timer("make vertices"):
            vertices = items.reshape(-1, items.shape[-1])
            if colors is not None:
                colors = colors.reshape(-1, colors.shape[-1])
            items = np.arange(len(vertices)).reshape(items.shape[:-1])
    return vertices, items, colors


def to_color_str(rgb):
    # rgb need to be int 0-255, opacity needs to be float 0.0-1.0
    args = ','.join(str(int(c*255)) for c in rgb[0:3])
    if len(rgb) == 3:
        color = f"rgb({args})"
    else:
        color = f"rgba({args},{rgb[3]:.2f})"
    return color

class Style:

    # color applies to points, lines, polys
    color = [0,0,0]
    @property
    def color_str(self):
        color_str = to_color_str(self.color)
        return color_str

    # edge_color applies to shape edges
    edge_color = [0,0,0,0]
    @property
    def edge_color_str(self):
        return to_color_str(self.edge_color)

    # similarly thickness for lines, edge_thickness for shape edges
    thickness = 1.5
    edge_thickness = 1.5


class FigureBuilder:

    # options are graphics_options
    def __init__(self, dim, fe, options):
        self.fe = fe
        self.dim = dim
        self.flat = False
        self.data = []
        self.opts = options
        self.has_image = False
        
        self.style = Style()


    def set_style(self, style):
        if style == 1:
            self.style0 = copy.copy(self.style)
        if style == 0:
            self.style = self.style0
            delattr(self, "style0")

    def set_color_rgb(self, rgb, ctx=None):

        assert len(rgb) == 3 or len(rgb) == 4

        if ctx == "edge":
            self.style.edge_color = rgb
        else:
            # FaceForm, plain RGBColor
            self.style.color = rgb

    def set_thickness(self, thickness, ctx=None):
        if ctx == "edge":
            self.style.edge_thickness = thickness
        else:
            self.style.thickness = thickness

    util.Timer("add_points")
    def add_points(self, vertices, points, colors):
        if vertices is not None:
            lines = vertices[lines]
        if self.dim == 2:
            scatter_points = go.Scatter(
                x = points[:,0], y = points[:,1],
                mode='markers', marker=dict(color=self.style.color_str, size=8)
            )
        elif self.dim == 3:
            # TODO: not tested
            scatter_points = go.Scatter3D(
                x = points[:,0], y = points[:,1], z = points[:,2],
                mode='markers', marker=dict(color=self.style.color_str, size=8)
            )
        self.data.append(scatter_points)

    util.Timer("add_lines")
    def add_lines(self, vertices, lines, colors):

        """
        # short-circuit em
        if isinstance(lines, (list,tuple)) and len(lines)==0 or \
           isinstance(lines, np.ndarray) and np.size(lines) == 0:
            return
        """

        if vertices is not None:
            lines = vertices[lines]

        # Concatenate lines, separating them with np.nan so they are
        # drawn as multiple line segments with a break between them.
        # We use nan instead of None so we can use nanmin and nanmax on the array.
        # also we can't rely on self.dim b/c classic density plot sends dim 3 mesh
        # TODO: track down why sometimes it's not coming through as an array
        dim = len(lines[0][0])
        single = [lines[0]]
        for line in lines[1:]:
            single.append([[np.nan] * dim])
            single.append(line)
        lines = np.vstack(single).reshape((-1, dim))

        if self.dim == 2:
            scatter_line = go.Scatter(
                x = lines[:,0], y = lines[:,1],
                mode='lines', line=dict(color=self.style.color_str, width=self.style.thickness),
                showlegend=False
            )
        elif self.dim == 3:
            scatter_line = go.Scatter3d(
                x = lines[:,0], y = lines[:,1], z = lines[:,2],
                mode='lines', line=dict(color=self.style.color_str, width=self.style.thickness),
                showlegend=False
            )
        self.data.append(scatter_line)

    # TODO: move triangulation inside?
    util.Timer("add_mesh")
    def add_polys(self, vertices, polys, colors):

        if self.dim==3:

            vertices, polys, colors = need_vertices(vertices, polys, colors)

            # TODO: only works well for nearly planar convex polys
            with util.Timer("triangulate"):
                ijks = []
                ngon = polys.shape[1]
                for i in range(1, ngon-1):
                    inx = [0, i, i+1]
                    tris = polys[:, inx]
                    ijks.extend(tris)
                ijks = np.array(ijks)

            # seems to be good default lighting
            lighting = dict(
                ambient = 0.5,
                roughness = 0.5,
                diffuse = 1.0,
                specular = 0.8,
                fresnel = 0.1
            )

            mesh = go.Mesh3d(
                x=vertices[:,0], y=vertices[:,1], z=vertices[:,2],
                i=ijks[:,0], j=ijks[:,1], k=ijks[:,2],
                lighting = lighting,
                lightposition = dict(x=10000, y=10000, z=10000),
                color = self.style.color_str,
                vertexcolor = colors,
                hoverinfo = "none"
            )

            self.data.append(mesh)

        elif self.dim==2:

            #
            # Plotly lacks something like Mesh2d so we have to find some workarounds
            #

            # TODO: find performance crossover?
            if len(polys) < 10:

                # use Scatter specifying each polygon as a marker
                # this case is for things like plots with Fill=...
                # that generate a single polygon or so
                if vertices is not None:
                    if colors is not None:
                        colors = colors[polys[:,0],:] * 255
                    polys = vertices[polys]
                for i, poly in enumerate(polys):
                    poly = np.array(poly)
                    # TODO: take averagee color instead of vertex 0 color[0]
                    color = None if colors is None else colors[i][0]
                    self._add_shape(poly[:,0], poly[:,1], color)

            else:

                # this case is for things like DensityPlot that generate
                # Polygon meshes

                # use mesh2d_markers
                #mesh = mesh2d.mesh2d_markers(vertices, polys, colors) # 600 ms

                # use mesh2d_opencv
                vertices, polys, colors = need_vertices(vertices, polys, colors)
                mesh = mesh2d.mesh2d_opencv(vertices, polys, colors, 200, 200) # 70 ms
                self.data.append(mesh)
                self.has_image = True

                # use mesh2d_svg
                # much too slow (>1 s)
                #mesh = mesh2d.mesh2d_svg(vertices, polys, colors)

                # try doing as flat 3d projection
                # problems: axis labels were wonky, lighting was wonky, scaling - ?
                # but this would leverage efficient mesh code...
                # if this code is removed, remove all self.flat options
                #self.dim = 3
                #self.flat = True
                #vertices = np.hstack([vertices, np.full(vertices.shape[0:2], 0.0)])
                #self.add_polys(vertices, polys, colors)

    def _add_shape(self, xs, ys, color=None):
        if color is None:
            fillcolor = self.style.color_str
            line_color = self.style.edge_color_str
        else:
            fillcolor = to_color_str(color)
            line_color = fillcolor
        trace = go.Scatter(
            x=xs, y=ys,
            mode="lines", fill="toself", fillcolor=fillcolor,
            line_width=self.style.edge_thickness, line_color=line_color
        )
        self.data.append(trace)

    def add_rectangles(self, vertices, rectangles, colors):
        for rectangle in rectangles:
            lo, hi = rectangle
            xs = [lo[0], lo[0], hi[0], hi[0]]
            ys = [lo[1], hi[1], hi[1], lo[1]]
            self._add_shape(xs, ys)

    def add_disks(self, vertices, disks, colors):
        for disk in disks:

            # center
            x, y = disk[0]
            
            # radii
            rx = ry = 1
            if len(disk) > 1:
                if isinstance(disk[1], (list,tuple,np.ndarray)):
                    rx, ry = disk[1]
                else:
                    rx = ry = disk[1]

            # angles
            a0, a1 = 0, 2 * np.pi
            if len(disk) > 2:
                a0, a1 = disk[2]
            ts = np.linspace(a0, a1, 100)

            # xs, ys
            xs = x + rx * np.cos(ts)
            ys = y + ry * np.sin(ts)

            # angle ends to center if not a full circle
            diff = (a0 - a1 + np.pi) %  (2 * np.pi) - np.pi
            if not np.isclose(diff, 0):
                xs = np.append(xs, x)
                ys = np.append(ys, y)

            self._add_shape(xs, ys)


    # TODO: should maybe be passed in using vertices and colors?
    # instead of this way?
    def add_insets(self, vertices, insets, colors):
        for (x, y), text in insets:
            trace = go.Scatter(x=[x], y=[y], mode="text", text=[text], textposition="middle center")
            self.data.append(trace)


    @util.Timer("figure")
    def figure(self):

        if not self.data:
            return

        # compute data_range
        with util.Timer("data_range"):
            if self.dim == 3:
                data = np.hstack([(trace.x, trace.y, trace.z) for trace in self.data])
            else:
                data = np.hstack([(trace.x, trace.y) for trace in self.data])
            data_range = np.array([np.nanmin(data, axis=1), np.nanmax(data, axis=1)]).T

        # get plot range either from opt or from data range
        plot_range = np.array([
            opt if isinstance(opt, list) else data
            for opt, data in zip(self.opts.plot_range, data_range)
        ])
        dx, dy, *_ = plot_range.T[1] - plot_range.T[0]

        # by this point width should be specified but
        # height may be None, requesting automatic computation
        width, height = self.opts.image_size
        if not height:
            height = width * dy / dx

        # expand sufficiently that lines and points
        # near edge of plot don't get cut in half,
        # and just generally curves have a bit of breathing room
        def expand(range, by=0.02):
            if self.dim==2 and not self.has_image:
                min, max = range
                delta = max - min
                range = [min - by*delta, max + by*delta]
            return range

        # compute axes options
        axes_opts = {}
        for i, p in enumerate("xyz" if self.dim==3 else "xy"):
            opts = dict(
                linecolor = "black",
                linewidth = 1 if self.dim==2 else 1.5, # TODO: look again
                range = expand(plot_range[i]),
                showgrid = False,
                showline = True,
                showspikes = False,
                ticks = "outside",
                title = None if self.dim==2 else "", # TODO: look again
                visible = self.opts.axes[i] or self.opts.frame,
            )
            if self.has_image and p == "y":
                # for Images plotly doesn't like to scale the image to fill the figure size,
                # so we force it to with this computation
                scaleratio = (height / width) * (dx / dy)
                opts |= dict(scaleanchor = "x", scaleratio = scaleratio)
            if self.dim == 3:
                opts |= dict(showbackground = False)
            axes_opts[p+"axis"] = opts

        # compute layout options
        layout_opts = dict(
            width = width,
            height = height,
            margin = dict(l=0, r=0, t=0, b=0),
            plot_bgcolor = 'rgba(0,0,0,0)',
            legend = None,
            showlegend = False,
            title = dict(text=""),  # Explicitly set title text to an empty string
        )

        if self.dim == 2:

            go_layout = go.Layout(**layout_opts, **axes_opts)

        elif self.dim == 3:

            # Boxed
            if not self.flat and self.opts.boxed:
                vertices = np.array(np.meshgrid(*plot_range)).reshape((3,-1)).T
                lines = [(i, i^k) for i in range(8) for k in [1,2,4] if not i&k]
                # TODO: safe because this is last, but really should have push/pop?
                self.set_color_rgb((0,0,0), None)
                self.add_lines(vertices, lines, None)

            # ViewPoint
            xyz_to_dict = lambda xyz: {n: v for n, v in zip("xyz", xyz)}
            if not self.flat:
                vp = self.opts.view_point
                vp = vp / la.norm(vp) * la.norm((1.25, 1.25, 1.25))
                camera = dict(eye = xyz_to_dict(vp))
            else:
                camera = dict(
                    eye = xyz_to_dict([0, 0, -1]),
                    projection_type = "orthographic"
                )

            # Put camera and BoxRatios together in scene
            # TODO: if not self.flat
            scene = dict(
                camera = camera,
                **axes_opts
            )
            # specified box ratios; otherwise Automatic, which lets figure choose
            if self.opts.box_ratios is not None:
                scene["aspectmode"] = "manual"
                scene["aspectratio"] = {
                    p: self.opts.box_ratios[i] for i, p in enumerate("xyz")
                }

            # combine above into final go_layout
            go_layout = go.Layout(**layout_opts, scene = scene)

        # combine data and g_layout into final figure
        with util.Timer("FigureWidget"):
            figure = go.Figure(data=self.data, layout=go_layout)

        # compute ticks for log plots
        if self.opts.log_plot:
            lo, hi = plot_range[1]
            #ticks = ticker.log_ticks_for_logged_data(log_vmin=lo, log_vmax=hi, base=10, minor=True)
            ticks = ticker.log10_ticks_for_logged_data_superscript(
                log_vmin=lo, log_vmax=hi, minor=True, nticks=6
            )
            figure.update_yaxes(**ticker.plotly_tick_array(ticks))

        # TODO: consider using for linear as well? plotly seems to do ok though
        #lo, hi = plot_range[0]
        #ticks = ticker.nice_linear_ticks(vmin=lo, vmax=hi, nticks=7)
        #figure.update_xaxes(**ticker.plotly_tick_array(ticks))        

        # if we're in test mode write the image
        if hasattr(self.fe, "test_image"):
            import plotly.io as pio
            pio.write_image(figure, self.fe.test_image)
            print("wrote", self.fe.test_image)
            
        return figure

