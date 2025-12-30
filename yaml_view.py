import os
import sys
import threading

if not "MATHICS3_TIMING" in os.environ:
    os.environ["MATHICS3_TIMING"] = "-1"

import panel
import yaml

import mathics.builtin.drawing.plot as plot
from mathics.core.convert.lambdify import CompileError

import core
import layout as lt
import util

panel.extension('plotly')

class FE:

    def __init__(self):

        self.session = core.MathicsSession()

        grid = panel.GridBox(
            ncols=3,
            sizing_mode="stretch_width",
            styles = {
                #"grid-template-columns": "1fr 1fr 1fr",
                #"grid-template-columns": "400px 400px 400px",
                "grid-auto-rows": "fit-content",  # fit content for each row
                "gap": "1em",
                #"align-items": "start",
            })
        shown = False

        # for each file on command line
        for fn in sys.argv[1:]:

            # extract tests to show
            split = fn.split(":", 1)
            fn = split[0]
            names = {}
            if len(split) > 1:
                names = set(split[1].split(","))

            # read the tests
            with open(fn) as r:
                tests = yaml.safe_load(r)

            # process each test
            for name, info in tests.items():

                # only do selected tests if requested
                if names and name not in names:
                    continue

                # process the expr
                str_expr = info.get("expr", None)
                if str_expr:

                    # add a caption
                    caption_str = f"{name}: {str_expr}"
                    print(f"=== {caption_str}")
                    caption = panel.pane.Markdown(caption_str, styles={"grid-column": "1 / -1"})
                    grid.extend([caption, "", ""])
                    
                    # if vec=True returns same as vec=False show N/A
                    last_ev_expr = None

                    for  vec in [False, True]:

                        # evaluate, lay out, append either layout or error message
                        layout = None
                        try:
                            plot.use_vectorized_plot = vec
                            ev_expr = self.session.evaluate(str_expr)
                            for message in self.session.evaluation.out:
                                print("MESSAGE:", message.text)
                            if str(ev_expr) != str(last_ev_expr) and "Graphics" in str(ev_expr.head):
                                layout = lt.expression_to_layout(self, ev_expr)
                                grid.append(layout)
                                if vec:
                                    print(f"VECTORIZED {caption_str}")
                            else:
                                grid.append("N/A")
                            last_ev_expr = ev_expr
                        except CompileError as oops:
                            msg = f"COMPILE: {oops}"
                            print(msg)
                            grid.append(msg)
                        except Exception as oops:
                            print(f"EXCEPTION: {type(oops)}: {oops}")
                            grid.append(str(oops))
                            
                        # show svg if not vec
                        if not vec:
                            if layout:
                                try:
                                    svg_str = layout._m3d_boxed.boxes_to_svg()
                                    svg_pane = panel.pane.SVG(svg_str, height=int(layout._m3d_height))
                                    grid.append(svg_pane)
                                except Exception as oops:
                                    print(f"EXCEPTION: {oops}")
                                    grid.append("EXCEPTION")
                            else:
                                grid.append("N/A")


            # getting some error if we show the grid then append items
            if not shown:
                util.show(grid, sys.argv[0])
                shown = True

FE()        

