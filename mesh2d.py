import util
import cv2
import numpy as np
import plotly.graph_objects as go


@util.Timer("mesh2d_opencv")
def mesh2d_opencv(vertices, polys, colors, nx=200, ny=200):

    # images of requested size
    img = np.full((nx,ny,3), 0, dtype=np.uint8)

    # scale vertices to nx, ny
    data_xs, data_ys = vertices[...,0], vertices[...,1]
    x_min, x_max = min(data_xs), max(data_xs)
    y_min, y_max = min(data_ys), max(data_ys)
    img_xs = (data_xs - x_min) / (x_max - x_min) * nx
    img_ys = (y_max - data_ys) / (y_max - y_min) * ny # cv2 is upside down
    
    # TODO: average poly color instead of vertex 0?
    colors = colors[polys[:,0],:] * 255

    # expand polys from indices to coordinates
    # seems not to like fp coordinates though
    img_xys = np.array([img_xs, img_ys]).T
    polys = img_xys[polys].astype(int)

    # render the polys
    for poly, color in zip(polys, colors):
        cv2.fillPoly(img, [poly], color)

    # go.Image doesn't have x, y arrays (unlike other graphic objects)
    # so we monkey-patch them in because we use it to compute data
    # range from all the graphic objects later on
    class Im(go.Image):
        def __init__(self, x, y, *args, **kwargs):
            super().__init__(*args, **kwargs)
            object.__setattr__(self, "x", x)
            object.__setattr__(self, "y", y)
            
    # construct our mesh to add to the figure
    # flip the image because opencv starts y from the top
    mesh = Im(
        z=img,
        x0=x_min, dx=(x_max-x_min)/nx, x=data_xs,
        y0=y_min, dy=(y_max-y_min)/ny, y=data_ys,
    )

    return mesh



@util.Timer("mesh2d_markers")
def mesh2d_markers(vertices, polys, colors):

        # Bit of a hack. There's no 2d go.Mesh, so we just do
        # a scatter plot of the points.
        # TODO: kind of slow in Plotly, so maybe resample to
        # a 100x100 grid might be faster overall? But kind of low-res...

        # flatten points
        points = polys if vertices is None else vertices
        points = points.reshape(-1, 2)

        if colors is not None:
            # flatten colors and stringify
            colors = colors.reshape(-1, 3)
            def to_rgb(color):
                args = ",".join(f"{int(c*255)}" for c in color)
                return f"rgb({args})"
            with util.Timer("add_polys to rgb"):
                colors = [to_rgb(c) for c in colors]
        else:
            colors = "black"

        mesh = go.Scatter(
            x=points[:,0], y=points[:,1],
            mode='markers', marker=dict(color=colors, size=4),
        )

        return mesh
