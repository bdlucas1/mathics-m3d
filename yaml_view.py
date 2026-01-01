import os
import sys
import threading
import time
import pathlib

import panel
import yaml
import pandas
import plotly

import mathics.builtin.drawing.plot as plot
from mathics.core.convert.lambdify import CompileError

import core
import layout as lt
import util

panel.extension('plotly')

def waitfor(d, k):
    while k not in d:
        print("xxx waiting for", k)
        time.sleep(1)
    return d[k]


class FE:

    def __init__(self):

        self.session = core.MathicsSession()
        self.shown = False

        self.grid = panel.GridBox(
            ncols=3,
            sizing_mode="stretch_width",
            styles = {
                #"grid-template-columns": "1fr 1fr 1fr",
                #"grid-template-columns": "400px 400px 400px",
                "grid-auto-rows": "fit-content",  # fit content for each row
                "gap": "1em",
                #"align-items": "start",
            })
        #self.show()

        # for each file on command line
        for fn in args.files:

            # extract tests to show
            split = fn.split(":", 1)
            fn = split[0]
            names = {}
            if len(split) > 1:
                names = set(split[1].split(","))

            # read the tests
            with open(fn) as r:
                tests = yaml.safe_load(r)

            self.ev_exprs = dict() # str_expr -> ev_expr
            self.layouts = dict() # str_expr -> layout

            # process each test
            for name, info in tests.items():

                # only do selected tests if requested
                if names and name not in names:
                    continue

                # process the expr
                str_expr = info.get("expr", None)
                if not str_expr:
                    continue

                # add a caption
                caption_str = f"{name}: {str_expr}"
                print(f"=== {caption_str}")
                caption = panel.pane.Markdown(caption_str, styles={"grid-column": "1 / -1"})
                self.grid.extend([caption, "", ""])

                self.grid.append(lambda: self.compute_plot(False, name, info, caption_str))
                self.grid.append(lambda: self.compute_svg(name, info))
                self.grid.append(lambda: self.compute_plot(True, name, info, caption_str))

            # getting some error if we show the grid then append items
            self.show()


    def show(self):
        if not self.shown:
            util.show(self.grid, sys.argv[0])
            self.shown = True

    # evaluate, lay out, return either layout or error message
    # stores non-vectorized layout for use by compute_svg
    def compute_plot(self, vec, name, info, caption_str):

        #if vec and not info.get("vec", True):
        #    return "SKIP"
        #if not vec and not info.get("cls", True):
        #    return "SKIP"

        str_expr = info["expr"]

        try:
            plot.use_vectorized_plot = vec
            ev_expr = self.session.evaluate(str_expr)
            for message in self.session.evaluation.out:
                print("MESSAGE:", message.text)
            if vec:
                nonvec_ev_expr = waitfor(self.ev_exprs, str_expr)
                if nonvec_ev_expr == ev_expr:
                    return "N/A"
                if not args.test:
                    print(f"VECTORIZED {caption_str}")
            else:
                self.ev_exprs[str_expr] = ev_expr
            if "Graphics" in str(ev_expr.head):
                layout = lt.expression_to_layout(self, ev_expr)
            else:
                layout = None
            if not vec:
                self.layouts[str_expr] = layout
            if layout:
                self.test(name, layout.object, "vec" if vec else "cls")
            return layout
        except CompileError as oops:
            msg = f"COMPILE: {oops}"
            print(msg)
            return msg
        except Exception as oops:
            msg = f"EXCEPTION in compute_plot: {type(oops)}: {oops}"
            print(msg)
            return msg

    # compute and retursn svg for str_expr
    # reuses layout computed by compute_plot
    def compute_svg(self, name, info):
        str_expr = info["expr"]
        layout = waitfor(self.layouts, str_expr)
        if layout:
            try:
                svg_str = layout._m3d_boxed.boxes_to_svg()
                svg_pane = panel.pane.SVG(svg_str, height=int(layout._m3d_height))
                self.test(name, svg_pane, "svg")
                return svg_pane
            except Exception as oops:
                msg = f"EXCEPTION in compute_svg: {oops}"
                #print(msg)
                return msg
        else:
            return "N/A"


    def test(self, name, item, kind):
        if args.test == "all" or kind in args.test:
            fn = pathlib.Path(__file__).resolve().parent / "yaml_test" / (f"{name}-{kind}.png")
            print("writing", fn)
            item.write_image(fn, scale=2)
        


import argparse
parser = argparse.ArgumentParser(description="yaml_view")
parser.add_argument("--test", nargs=1, type=str)
parser.add_argument("files", nargs="*", type=str)
args = parser.parse_args()

if not "MATHICS3_TIMING" in os.environ:
    if args.test:
        os.environ["MATHICS3_TIMING"] = "0"
    else:
        os.environ["MATHICS3_TIMING"] = "-1"

FE()        

