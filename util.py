import os
import sys
import time
import traceback
import urllib.parse
import webbrowser
import importlib
import subprocess
import panel as pn
import pathlib

from mathics.core.util import *
from mathics.timing import *

def resource(fn):
    return  str(pathlib.Path(__file__).resolve().parent / fn)

try:
    import webview
except:
    webview = None

def print_stack_reversed(file=None):
    """Print the current stack trace, from innermost to outermost."""
    if file is None:
        file = sys.stderr
    stack = traceback.extract_stack()
    for frame in reversed(stack):
        print(f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}', file=file)
        if frame.line:
            print(f'    {frame.line.strip()}', file=file)            

def print_exc_reversed(exc_info=None, file=None):
    """Like traceback.print_exc(), but prints traceback frames in reverse order (innermost to outermost)."""
    if exc_info is None:
        exc_info = sys.exc_info()
    if file is None:
        file = sys.stderr

    etype, value, tb = exc_info
    if tb is None:
        print("No active exception", file=file)
        return

    stack = traceback.extract_tb(tb)
    print("Traceback (most recent call last, reversed):", file=file)
    for frame in reversed(stack):
        print(f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}', file=file)
        if frame.line:
            print(f'    {frame.line.strip()}', file=file)
    print(f"{etype.__name__}: {value}", file=file)


#
# print expr as a tree
#

def prt_expr_tree(expr, indent=1):
    if not hasattr(expr, "elements"):
        print("  " * indent + str(expr))
    else:
        print("  " * indent + str(expr.head))
        for elt in expr.elements:
            prt_expr_tree(elt, indent + 1)

def prt_sympy_tree(expr, indent=""):
    if expr.args:
        print(f"{indent}{expr.func.__name__}")
        for i, arg in enumerate(expr.args):
            prt_sympy_tree(arg, indent + "    ")
    else:
        print(f"{indent}{expr.func.__name__}({str(expr)})")


#
#
#

# load a url into a browser, using either:
# webview - pop up new standalone window using pywebview
# webbrowser - instruct system browser to open a new window
class Browser:

    def __init__(self, browser=None):
        self.n = 0
        self.browser = browser or os.getenv("DEMO_BROWSER", "webview")
        if not webview:
            self.browser = "webbrowser"

    def show(self, url, width=700, height=1000, title=None):
        # display a browser window that fetches the current plot
        #print("showing", url)
        if self.browser == "webview":
            offset = 50 * self.n
            self.n += 1
            title = title or url
            webview.create_window(title, url, x=100+offset, y=100+offset, width=width, height=height, zoomable=True)
        elif self.browser == "webbrowser":
            webbrowser.open_new(url)
        else:
            subprocess.run(["open", "-a", self.browser, url])
        return self

    def start(self):

        if self.browser == "webview":
            # webview needs to run on main thread :( and blocks, so we start other things on their own thread
            # webview needs a window before we can call start() :(, so we make a hidden one
            # real windows will be provided later
            webview.create_window("hidden", hidden=True)
            webview.start()
        return self

def show(app, title, browser=None):

    # find a free port
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))  # Bind to an ephemeral port chosen by the OS
        port = s.getsockname()[1]  # Return the assigned port number

    # start the server
    server = pn.serve(
        app,
        port=port,
        address="localhost",
        threaded=True,
        show=False,
        title=title,
    )

    # start a browser
    Browser(browser).show(f"http://localhost:{port}", title=title).start()
    


import sys
import traceback
import threading

def my_excepthook(exc_type, exc, tb):
    print("\n=== Uncaught exception (reversed stack via PYTHONPATH and ~/bin/sitecustomize.py) ===", file=sys.stderr)

    # Extract frames and reverse them
    frames = traceback.extract_tb(tb)
    for frame in reversed(frames):
        # This format matches traceback formatting but reversed:
        print(f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}', file=sys.stderr)
        if frame.line:
            print(f"    {frame.line.strip()}", file=sys.stderr)

    # Print exception type + message
    print(f"{exc_type.__name__}: {exc}", file=sys.stderr)

sys.excepthook = my_excepthook
print("loading excepthook")

# Handle uncaught exceptions in threads (Python 3.8+)
try:
    def _thread_hook(args):
        my_excepthook(args.exc_type, args.exc_value, args.exc_traceback)
    threading.excepthook = _thread_hook
except Exception:
    print("not loading thread excepthook")
    pass
    
