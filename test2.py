import os
os.environ["MATHICS3_USE_VECTORIZED_PLOT"] = "yes"
os.environ["MATHICS3_TIMING"] = "1"


import panel as pn
import plotly
import plotly.io as pio
import plotly.graph_objects as go
import skimage.transform
import skimage.io
import PIL
import numpy as np

import util


top = pn.Column(styles={"gap": "1em"})
util.show(top, "TEST", browser="webbrowser")
#pn.serve(top, port=9999, threaded=True, show=False)
#util.Browser().show("http://localhost:9999", width=300, height=300, title="foo")


def test(fn, layout):

    print("=== TEST", fn, layout)

    # wrap image together with caption in a column
    def img(cap, im):
        im = PIL.Image.fromarray(im)
        im = pn.pane.Image(im, width=im.width, sizing_mode='fixed')
        cap = pn.widgets.StaticText(value=cap)
        return pn.Column(cap, im)

    # file names
    fn_ref = f"{fn}.png"
    fn_test = f"/tmp/{fn.replace('/','-')}.png"

    # get figures - pio.write_image only works with Figures
    def collect_figures(x):
        if isinstance(x, go.Figure):
            yield x
        elif isinstance(x, pn.pane.Plotly):
            yield x.object
        elif isinstance(x, (list,tuple)):
            for xx in x:
                yield from collect_figures(xx)
    collect_figures(layout)
    figures = [*collect_figures(layout)]
    assert len(figures) == 1

    # write the figure
    # TODO: try layou.save again - requires Selenium
    pio.write_image(figures[0], fn_test) # only works for Figures
    im_test = skimage.io.imread(fn_test)[:,:,0:3]

    row, cap = None, None
    if not os.path.exists(fn_ref):
        # ref image does not exist
        row = pn.Row(img("actual", im_test))
        cap = f"Save test image"
    else:
        # ref image exists - compare
        im_ref = skimage.io.imread(fn_ref)[:,:,0:3]
        if im_test.shape != im_ref.shape:
            print(f"=== shapes differ: test {im_test.shape}, ref {im_ref.shape}")
            row = pn.Row(img("actual",im_test), img(f"expected {fn_ref}",im_ref))
            cap = "Update expected image"
        elif not (im_ref - im_test == 0).all():
            print("=== images differ")
            im_diff = abs(im_test.astype(float) - im_ref.astype(float)) # avoid overflow
            print("max pixel diff", np.max(im_diff))
            im_diff = im_diff.astype(np.uint8)
            row = pn.Row(img("actual",im_test), img(f"expected {fn_ref}",im_ref), img("diff",im_diff))
            cap = "Update expected image"
        else:
            print("=== images are identical")
        
    # if there was a diff show it and ask
    if row:
        button = pn.widgets.Button(name=cap, styles={"font-size": "12pt"})
        def copy(_):
            print(f"copying {fn_test} to {fn_ref}")
            with open(fn_test, "rb") as f_test:
                img_data = f_test.read()
                with open(fn_ref, "wb") as f_ref:
                    f_ref.write(img_data)
            top.remove(row)
            top.remove(button)
        button.on_click(copy)
        top.append(row)
        top.append(button)


    # TODO: WIP
    # ff formats too wide, so fix that first
    #layout.save(f"/tmp/{fn_m.split('/')[-1]}-test.png")
    #
