import os
import sys
import threading

if not "MATHICS3_TIMING" in os.environ:
    os.environ["MATHICS3_TIMING"] = "-1"

import panel
import yaml

import mathics.builtin.drawing.plot as plot

import core
import layout as lt
import util

panel.extension('plotly')

class FE:

    def __init__(self):

        self.session = core.MathicsSession()

        grid = panel.GridBox(
            ncols=2,
            sizing_mode="stretch_width",
            styles = {
                "grid-template-columns": "1fr 1fr",
                "grid-auto-rows": "max-content",  # fit content for each row
                "gap": "12px 16px",
                "align-items": "start",
            })
        shown = False


        for fn in sys.argv[1:]:

            with open(fn) as r:
                tests = yaml.safe_load(r)

            for name, info in tests.items():
                str_expr = info.get("expr", None)
                if str_expr:
                    caption = f"{name}: {str_expr}"
                    print(f"=== {caption}")
                    caption = panel.pane.Markdown(f"### {caption}", styles={"grid-column": "1 / -1"})
                    grid.extend([caption, ""])
                    last_ev_expr = None
                    for grid_col, vec in enumerate([False, True]):
                        try:
                            plot.use_vectorized_plot = vec
                            ev_expr = self.session.evaluate(str_expr)
                            for message in self.session.evaluation.out:
                                print("MESSAGE:", message.text)
                            if str(ev_expr) != str(last_ev_expr) and "Graphics" in str(ev_expr.head):
                                layout = lt.expression_to_layout(self, ev_expr)
                                grid.append(layout)
                            else:
                                grid.append("N/A")
                            last_ev_expr = ev_expr
                        except Exception as oops:
                            print(f"EXCEPTION: {oops}")
                            grid.append(str(oops))
                            

            if not shown:
                util.show(grid, sys.argv[0])
                shown = True

FE()        

