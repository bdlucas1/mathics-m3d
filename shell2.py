import os
import threading
import time
import socket

import mathics.builtin.drawing.plot
mathics.builtin.drawing.plot.use_vectorized_plot = True

# this is not really part of m3d per se - in this demo it's just
# a standin for lots of imports from mathics
import core

try:
    import panel as pn
    import util
    import m3dlib
except:
    m3dlib = None

    
# pick one:
mode = "webview" # pops up a new dedicated window for every output
#mode = "webbrowser" # opens a browser window/tab using system browser for every output


class FE:

    def __init__(self):

        self.session = core.MathicsSession()
        self.app = None

        self.browser = util.Browser(mode)

        if mode == "webview":

            # start the REPL on its own thread
            threading.Thread(target=self.repl).start()

            # for webview this has to run on main thread and it blocks
            # so we do it last
            self.browser.start()

        else:

            # for webbrowser mode we can just run the REPL
            # on the main thread
            self.repl()


    def repl(self):

        while True:

            # get input expr_str
            try:
                expr_str = input("i> ")
            except EOFError:
                print("bye")
                os._exit(0)
            if not expr_str:
                continue

            try:
                # evaluate
                expr = self.session.parse(expr_str)
                expr = expr.evaluate(self.session.evaluation)

                # show output
                print("o>", expr.head if hasattr(expr, "head") else str(expr))

                # suppose we decided we got graphics - use m3d to display it
                if True:
                    if not self.app:
                        self.app = m3dlib.App(load=None, session=self.session)
                        self.show(self.app, title="shell graphical output")
                    pair = m3dlib.Pair(self.app, text=expr_str, run=True, input_visible=True)
                    self.app.view.append(pair)
                    pair.update()

            except Exception as oops:
                print(oops)
                continue

    def show(self, top, title):

        # find a free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))  # Bind to an ephemeral port chosen by the OS
            port = s.getsockname()[1]  # Return the assigned port number

        # start the server on its own thread
        server = pn.serve(
            top,
            port=port,
            address="localhost",
            threaded=True,
            show=False,
        )
        time.sleep(0.1)

        # aim a browser window at it
        self.browser.show(f"http://localhost:{port}", title=title)


if __name__ == "__main__":
    FE()

    

