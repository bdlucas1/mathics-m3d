import os
os.environ["MATHICS3_TIMING"] = "1"

import time
import pathlib
import copy

import panel as pn
import plotly
import plotly.io as pio
import plotly.graph_objects as go
import skimage.transform
import skimage.io
import PIL
import numpy as np

import util

class State: pass
state = State()

state.pending = 0
state.run = 0
state.missing = 0
state.failed = 0
state.passed = 0
state.fixed = 0

def summarize_and_exit():
    msg = f"=== {state.run} run, {state.passed} passed, {state.failed} failed, {state.fixed} fixed"
    print(msg)
    msg = pn.widgets.StaticText(value=msg)
    state.top[:] = [x for x in state.top if not isinstance(x, pn.widgets.Button)] + [msg]
    time.sleep(1)
    os._exit(0)

state.top = pn.Column(
    heading := pn.pane.Str("Running tests "),
    styles={"gap": "1em"}
)
util.show(state.top, "TEST", browser="webbrowser")

# track pending tests so we know when we're done
def pending():
    state.pending += 1

def test(test_info, layout, expr):

    # do it up front in case we return early as this is used
    # to know when we are done
    state.pending -= 1

    fn = test_info["fn"]
    test_name = test_info["test"]

    # compute test filename fn
    if test_name := test_info["test"]:
        base_fn, _ =  os.path.splitext(fn)
        fn = f"{base_fn}={test_name}" # = sorts after .
    else:
        # this was a freestanding .m file
        fn, _ = os.path.splitext(fn)

    print("=== TEST", fn) #, layout)
    heading.object += "."
    state.run += 1

    # wrap image together with caption in a column
    def img(cap, im):
        im = PIL.Image.fromarray(im)
        im = pn.pane.Image(im, width=im.width, sizing_mode='fixed')
        cap = pn.widgets.StaticText(value=cap)
        return pn.Column(cap, im)

    # file names
    path = pathlib.Path(fn)
    fn_ref = path.parent / "@ref" / (path.name + ".png")
    fn_test = f"/tmp/{fn.replace('/','-')}.png"
    fn_dump = f"/tmp/{fn.replace('/','-')}.txt"

    # get figures - pio.write_image only works with Figures
    def collect_figures(x):
        if isinstance(x, go.Figure):
            yield x
        elif isinstance(x, pn.pane.Plotly):
            yield x.object
        else:
            try:
                for xx in x:
                    if xx is not x:
                        yield from collect_figures(xx)
            except TypeError as oops:
                #print(oops)
                pass

    mode = test_info.get("mode", "figure")
    if mode == "figure":

        # find a figure and write it
        collect_figures(layout)
        figures = [*collect_figures(layout)]
        if len(figures) == 0:
            state.failed += 1
            print("NO FIGURES")
            return

        # write only last figure
        figure = figures[-1] # mimic previous behavior
        if not figure:
            print("FAIL: figure is None")
            return
        pio.write_image(figure, fn_test) # only works for Figures

    elif mode == "layout":

        # save entire layout
        # hack: this cuts off a bit of the right side, so we pad it
        hack = pn.Row(layout, pn.Spacer(width=100))
        hack.save(fn_test)

    # read image back int
    im_test = skimage.io.imread(fn_test)[:,:,0:3]

    # dump expr for debugging
    with open(fn_dump, "w") as f:
        util.print_expression_tree(expr, file=f, approximate=True)

    # compare
    row, cap = None, None
    if not os.path.exists(fn_ref):
        print(f"=== ref image {fn_ref} does not exist")
        state.missing += 1
        row = pn.Row(img("actual", im_test))
        cap = f"Save test image as {fn_ref}"
    else:
        # ref image exists - compare
        im_ref = skimage.io.imread(fn_ref)[:,:,0:3]
        if im_test.shape != im_ref.shape:
            print(f"=== shapes differ: test {im_test.shape}, ref {im_ref.shape}")
            state.failed += 1
            row = pn.Row(img("actual",im_test), img(f"expected {fn_ref}",im_ref))
            cap = "Update expected image"
        elif not (im_ref - im_test == 0).all():
            print("=== images differ")
            state.failed += 1
            im_diff = abs(im_test.astype(float) - im_ref.astype(float)) # avoid overflow
            print("max pixel diff", np.max(im_diff))
            im_diff = im_diff.astype(np.uint8)
            row = pn.Row(img("actual",im_test), img(f"expected {fn_ref}",im_ref), img("diff",im_diff))
            cap = "Update expected image"
        else:
            print("=== images are identical")
            state.passed += 1
        
    # if there was a diff show it and ask
    if row:
        button = pn.widgets.Button(name=cap, styles={"font-size": "12pt"})
        def copy(_):
            print(f"=== copying {fn_test} to {fn_ref}")
            state.fixed += 1
            with open(fn_test, "rb") as f_test:
                img_data = f_test.read()
                with open(fn_ref, "wb") as f_ref:
                    f_ref.write(img_data)
            state.top.remove(row)
            state.top.remove(button)
        button.on_click(copy)
        state.top.append(row)
        state.top.append(button)

    # if we've seen all tests we were promised and there were no failures just exit
    # otherwise the user will have to press the "Finish" button
    if state.pending == 0:
        if state.failed == 0 and state.missing == 0:
            summarize_and_exit()
        else:
            finish_button = pn.widgets.Button(name="Finish")
            finish_button.on_click(lambda _: summarize_and_exit())
            state.top.append(finish_button)
            print("=== there were failures - finish in browser window")
            

    # TODO: WIP
    # ff formats too wide, so fix that first
    #layout.save(f"/tmp/{fn_m.split('/')[-1]}-test.png")
    #

