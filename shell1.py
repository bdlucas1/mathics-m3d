import os
import threading
import time
import socket

import panel as pn

import mathics.builtin.drawing.plot
mathics.builtin.drawing.plot.use_vectorized_plot = True

import core
import layout as lt
import util
import ui

# pick one:
mode = "webview" # pops up a new dedicated window for every output
#mode = "webbrowser" # opens a browser window/tab using system browser for every output


class FE:

    def __init__(self):

        self.session = core.MathicsSession()

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
            try:
                expr_str = input("> ")
            except EOFError:
                print("bye")
                os._exit(0)
            if not expr_str:
                continue
            try:
                expr = self.session.parse(expr_str)
                expr = expr.evaluate(self.session.evaluation)
                layout = lt.expression_to_layout(self, expr)        
                top = pn.Column(layout, styles={"margin-top": "40px"})
                self.show(top, title=expr_str)
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

    

