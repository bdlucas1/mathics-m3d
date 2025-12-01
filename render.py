import numpy as np
import numpy.linalg as la
import plotly.graph_objects as go
import os

import mesh2d
import util


# TODO: move to consumer
def need_vertices(vertices, items):
    if vertices is None:
        with util.Timer("make vertices"):
            vertices = items.reshape(-1, items.shape[-1])
            items = np.arange(len(vertices)).reshape(items.shape[:-1])
    return vertices, items

class FigureBuilder:

    # options are graphics_options
    def __init__(self, dim, fe, options):
        self.fe = fe
        self.dim = dim
        self.flat = False
        self.data = []
        self.img_array = None
        self.opts = options
        
        
        # rendering options
        self.color = "gray"
        self.thickness = 1.5

    def set_color_rgb(self, rgb, ctx=None):
        assert len(rgb) == 3 or len(rgb) == 4
        t = "rgb" if len(rgb) == 3 else "rgba"
        args = ','.join(str(int(c*255)) for c in rgb)
        color = f"{t}({args})"
        if ctx is None:
            self.color = color
        else:
            print(f"ctx {ctx} not supported")

    util.Timer("add_points")
    def add_points(self, vertices, points, colors):
        if vertices is not None:
            lines = vertices[lines]
        if self.dim == 2:
            scatter_points = go.Scatter(
                x = points[:,0], y = points[:,1],
                mode='markers', marker=dict(color=self.color, size=8)
            )
        elif self.dim == 3:
            # TODO: not tested
            scatter_points = go.Scatter3D(
                x = points[:,0], y = points[:,1], z = points[:,2],
                mode='markers', marker=dict(color=self.color, size=8)
            )
        self.data.append(scatter_points)

    util.Timer("add_lines")
    def add_lines(self, vertices, lines, colors):

        if vertices is not None:
            lines = vertices[lines]

        # Concatenate lines, separating them with np.nan so they are
        # drawn as multiple line segments with a break between them.
        # We use nan instead of None so we can use nanmin and nanmax on the array.
        single = [lines[0]]
        for line in lines[1:]:
            single.append([[np.nan] * self.dim])
            single.append(line)
        lines = np.vstack(single).reshape((-1, self.dim))

        if self.dim == 2:
            scatter_line = go.Scatter(
                x = lines[:,0], y = lines[:,1],
                mode='lines', line=dict(color=self.color, width=self.thickness),
                showlegend=False
            )
        elif self.dim == 3:
            scatter_line = go.Scatter3d(
                x = lines[:,0], y = lines[:,1], z = lines[:,2],
                mode='lines', line=dict(color=self.color, width=self.thickness),
                showlegend=False
            )
        self.data.append(scatter_line)

    # TODO: move triangulation inside?
    util.Timer("add_mesh")
    def add_polys(self, vertices, polys, colors):

        if self.dim==3:

            vertices, polys = need_vertices(vertices, polys)

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
                color = self.color,
                vertexcolor = colors,
                hoverinfo = "none"
            )

            self.data.append(mesh)

        elif self.dim==2:

            if True:
                #mesh = mesh2d.mesh2d_markers(vertices, polys, colors) # 600 ms
                mesh = mesh2d.mesh2d_opencv(vertices, polys, colors, 200, 200) # 70 ms
                self.data.append(mesh)

            else:
                # try doing as flat 3d projection
                # problems: axis labels were wonky, lighting was wonky, scaling - ?
                # if this code is removed, remove all self.flat options
                self.dim = 3
                self.flat = True
                vertices = np.hstack([vertices, np.full(vertices.shape[0:2], 0.0)])
                self.add_polys(vertices, polys, colors)

    @util.Timer("figure")
    def figure(self):

        # compute data_range
        with util.Timer("data_range"):
            if self.dim == 3:
                data = np.hstack([(trace.x, trace.y, trace.z) for trace in self.data])
            else:
                data = np.hstack([(trace.x, trace.y) for trace in self.data])
            data_range = np.array([np.nanmin(data, axis=1), np.nanmax(data, axis=1)]).T

        # get plot range either from opt or from data range
        plot_range = [
            opt if isinstance(opt, list) else data
            for opt, data in zip(self.opts.plot_range, data_range)
        ]

        # compute axes options
        axes_opts = {}
        for i, p in enumerate("xyz" if self.dim==3 else "xy"):
            opts = dict(
                linecolor = "black",
                linewidth = 1 if self.dim==2 else 1.5, # TODO: look again
                range = plot_range[i],
                showgrid = False,
                showline = True,
                showspikes = False,
                ticks = "outside",
                title = None if self.dim==2 else "", # TODO: look again
                visible = self.opts.axes[i] or self.opts.frame,
            )
            if self.dim == 2 and p == "y":
                # for Images plotly doesn't like to scale the image to fill the figure size,
                # so we force it to with this computation
                # TODO: is there a single boolean that will make it do this?
                pr = np.array(plot_range).T
                dr = pr[1] - pr[0]
                isz = self.opts.image_size
                scaleratio = (isz[1] / isz[0]) * (dr[0] / dr[1])
                opts |= dict(scaleanchor = "x", scaleratio = scaleratio)
            if self.dim == 3:
                opts |= dict(showbackground = False)
            axes_opts[p+"axis"] = opts

        # compute layout options
        layout_opts = dict(
            height = self.opts.image_size[1],
            legend = None,
            margin = dict(l=0, r=0, t=0, b=0),
            plot_bgcolor = 'rgba(0,0,0,0)',
            showlegend = False,
            title = dict(text=""),  # Explicitly set title text to an empty string
            width = self.opts.image_size[0],
        )

        if self.dim == 2:

            go_layout = go.Layout(**layout_opts, **axes_opts)

        elif self.dim == 3:

            # Boxed
            if not self.flat and self.opts.boxed:
                vertices = np.array(np.meshgrid(*plot_range)).reshape((3,-1)).T
                lines = [(i, i^k) for i in range(8) for k in [1,2,4] if not i&k]
                # TODO: safe because this is last, but really should have push/pop?
                self.set_color_rgb((0,0,0))
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

            # BoxRatios
            box_ratios = self.opts.box_ratios if not self.flat else [1, 1, 1]
            scene = dict(
                aspectmode = "manual",
                aspectratio = {p: box_ratios[i] for i, p in enumerate("xyz")},
                camera = camera,
                **axes_opts
            )

            # combine above into final go_layout
            go_layout = go.Layout(**layout_opts, scene = scene)

        # combine data and g_layout into final figure
        with util.Timer("FigureWidget"):
            figure = go.Figure(data=self.data, layout=go_layout)

        # if we're in test mode write the image
        if hasattr(self.fe, "test_image"):
            import plotly.io as pio
            pio.write_image(figure, self.fe.test_image)
            print("wrote", self.fe.test_image)
            
        return figure

