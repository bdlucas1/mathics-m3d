import os
import threading
import time
import socket

import mathics.builtin.drawing.plot
mathics.builtin.drawing.plot.use_vectorized_plot = True

from mathics.session import MathicsSession

try:
    import util
    import m3dlib
except:
    m3dlib = None

    
# pick one:
browser = "webview" # pops up a new dedicated window for every output
#browser = "webbrowser" # opens a browser window/tab using system browser for every output


class Shell:

    def __init__(self):
        self.session = MathicsSession()
        self.m3d_app = None

    def repl(self):

        # the L in REPL
        while True:

            # get input expr_str
            try:
                expr_str = input("\ni> ")
            except EOFError:
                print("bye")
                os._exit(0)
            if not expr_str:
                continue

            try:
                # evaluate
                self.session.evaluation.out.clear()
                expr = self.session.parse(expr_str)
                expr = expr.evaluate(self.session.evaluation)

                # here's where we show output on terminal
                print("\no>", expr.head if hasattr(expr, "head") else str(expr))

                # suppose we got graphics, and m3d is available
                # then use m3d to display it
                has_graphics = True
                if has_graphics and m3dlib:

                    # create m3d App if needed, else use the existing one
                    m3d_app = self.m3d_app or m3dlib.App(load=None, session=self.session)

                    # append an input/output pair to the m3d App
                    # this wraps up a couple calls in m3dlib, which limits options
                    # but narrows the interface. Could be widened if needed.
                    # we pass it the evaluated expr to display, and it will pick up
                    # messages from the session
                    m3d_app.append_evaluated_pair(text=expr_str, expr=expr)

                    # show the m3d App if we just created it
                    # if using webview it needs the main thread, and util.show blocks,
                    # so we continue the REPL on a new thread
                    # (and this has to be at the bottom of the loop)
                    if not self.m3d_app:
                        self.m3d_app = m3d_app
                        if browser == "webview":
                            threading.Thread(target=self.repl).start()
                        util.show(m3d_app, title="shell graphical output", browser=browser)

            except Exception as oops:
                print(oops)
                #raise
                continue


if __name__ == "__main__":
    # run REPL on the main thread
    Shell().repl()
