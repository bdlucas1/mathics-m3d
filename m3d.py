import sys
sys.stdout.flush()

import os
os.environ["DEMO_USE"] = "panel"
os.environ["MATHICS3_TIMING"] = "-1"

import threading
import re

import panel as pn
import panel.widgets as pnw
import plotly.express as px
import plotly.graph_objects as go
import param

import core
import sym
import layout as lt
import os
import util
import hook
import sys
import time
import ui

pn.extension('plotly')
pn.extension('mathjax')
pn.extension(raw_css=[open('m3d.css').read()])

class FE:
    def __init__(self):
        self.session = core.MathicsSession()
        pass

fe = FE()


#
# An input-output pair, as a column
#

class Pair(pn.Column):

    def __init__(self, text=None, input_visible=False):
        
        self.old_expr = ""

        # input
        instructions = "Type expression followed by shift-enter"
        self.input = pn.widgets.TextAreaInput(
            placeholder = instructions,
            value = text,
            value_input = text,
            auto_grow = True,
            max_rows = 9999,
            sizing_mode = "stretch_width",
            css_classes = ["m-input"],
            # TODO: alwyas initially not visible?
            visible = input_visible,
        )

        # track as user types
        def input_changed(event):
            self.is_stale = self.old_expr != self.input.value_input
            self.exec_button.visible = self.is_stale
        self.input.param.watch(input_changed, "value_input")

        # edit button toggles input code block visibility
        def toggle_input():
            self.input.visible = not self.input.visible
        self.edit_button = ui.icon_button(
            "edit",
            "Toggle code block\nfor editing",
            toggle_input
        )

        # execute code if stale
        self.exec_button = ui.icon_button(
            "alert-triangle",
            "Output is stale; click or\ntype cmd+enter\nto execute code", 
            self.update_if_changed
        )
        self.exec_button.visible = False

        # put the buttons together
        buttons = pn.Column(
            self.edit_button,
            self.exec_button,
            css_classes = ["m-button-column"]
        )

        # output
        self.output = pn.Row(
            None, # actual output goes here
            buttons,
            css_classes = ["m-output"],
            # TODO: extract from .css file?
            styles=dict(width="fit-content", gap="1em")
        )

        # make us a column consisting of the input followed by the output
        # input may be invisible if not in edit mode
        super().__init__(self.input, self.output, css_classes=["m-pair"])

        # initial content
        self.update_if_changed(force=True)

    # check whether input has changed, and eval if so
    def update_if_changed(self, force=False):
        expr = self.input.value_input
        if expr and (force or self.is_stale):
            with util.Timer("execute code block"):
                expr = fe.session.parse(expr)
                expr = expr.evaluate(fe.session.evaluation)
                layout = lt.expression_to_layout(fe, expr)
                self[1][0] = layout
            self.old_expr = expr
            self.is_stale = False
            self.exec_button.visible = False
            
                
#
# cmd+enter executes all changed
#

def update_changed(force=False):
    for item in the_app:
        if isinstance(item, Pair):
            item.update_if_changed(force=force)

shortcuts = ui.KeyboardShortcuts(shortcuts=[
    ui.KeyboardShortcut(name="run", key="Enter", ctrlKey=True),
    ui.KeyboardShortcut(name="run", key="Enter", altKey=True),
    ui.KeyboardShortcut(name="run", key="Enter", metaKey=True),
    ui.KeyboardShortcut(name="run_force", key="Enter", ctrlKey=True, shiftKey=True),
    ui.KeyboardShortcut(name="run_force", key="Enter", altKey=True, shiftKey=True),
    ui.KeyboardShortcut(name="run_force", key="Enter", metaKey=True, shiftKey=True),
])

def shortcut_msg(event):
    if event.data == "run":
        update_changed()
    if event.data == "run_force":
        update_changed(force=True)
shortcuts.on_msg(shortcut_msg)

#
# function to construct the app
# we pass this to pn.serve so it can construct
# the app when it's good and ready (see comment below)
#

#class App(pn.Feed):
class App(pn.Column):

    def __init__(self, load):

        buttons = pn.Row(
            pn.widgets.ButtonIcon(icon="help"),
            pn.widgets.ButtonIcon(icon="file-plus"),
            pn.widgets.ButtonIcon(icon="file-download"),
            pn.widgets.ButtonIcon(icon="file-upload"),
            pn.widgets.ButtonIcon(icon="edit"),
            pn.widgets.ButtonIcon(icon="player-play"),
            pn.widgets.ButtonIcon(icon="clipboard-text"),
            #pn.widgets.ButtonIcon(icon="mood-smile"),
            #pn.widgets.ButtonIcon(icon="mood-confuzed"),
            #pn.widgets.ButtonIcon(icon="alert-triangle"),
            #pn.widgets.ButtonIcon(icon="square-x"),
            #pn.widgets.ButtonIcon(icon="heart"),
            #pn.widgets.ButtonIcon(icon="file-pencil"),    
            #pn.widgets.ButtonIcon(icon="player-track-next"),
            css_classes=["m-button-row"]
        )

        # now we're a column
        super().__init__(
            shortcuts,
            buttons,
            css_classes=["m-app"]
        )

        if load:
            fns = "data/gallery.m3d" if "pyodide" in sys.modules else sys.argv[1:]
            #from panel.io import hold
            #with hold():
            self.load_files(fns)


    def load_m3d(self, md_fn):
        print("loading", md_fn)
        md_str = open(md_fn).read()
        # TODO: allow for tags or instructions after ``` until end of line
        md_parts = re.split("(```)", md_str)
        is_m3 = False
        for part in md_parts:
            if part == "```":
                is_m3 = not is_m3
            elif is_m3:
                pair = Pair(part.strip())
                self.append(pair)
                # TODO: autorun optional?
                pair.update_if_changed(force=True)
            else:
                #help(pn.pane.Markdown)
                md = pn.pane.Markdown(
                    part,
                    disable_math = False,
                    css_classes=["m-markdown"],
                    # TODO: extract from .css file
                    stylesheets=["""
                        * {
                            font-family: sans-serif;
                            font-size: 12pt;
                            line-height: 1.4;
                        }
                        h1 {font-size: 20pt; margin-top: 1.0em; &:first-child {margin-top: 0em;}}
                        h2 {font-size: 18pt; margin-top: 0.8em; &:first-child {margin-top: 0em;}}
                        h3 {font-size: 16pt; margin-top: 0.6em; &:first-child {margin-top: 0em;}}
                        h4 {font-size: 24pt; margin-top: 0.4em; &:first-child {margin-top: 0em;}}
                    """]
                )
                self.append(md)

    def load_m(self, m_fn):
        m_str = open(m_fn).read()    
        pair = Pair(m_str.strip())
        self.append(pair)

    def load_files(self, fns):
        if len(fns):
            for fn in fns:
                if fn.endswith(".m3d"):
                    self.load_m3d(fn)
                elif fn.endswith(".m"):
                    self.load_m(fn)
                else:
                    print(f"Don't understand file {fn}")
        else:
            self.append(Pair(None, input_visible=True))



#
# startup action depends on mode -
# building for pyodide, running under pyodide, or running as a server
#

if "DEMO_BUILD_PYODIDE" in os.environ:
    print("building for pyodide")
    app = App(load=False)
    app.servable()
elif "pyodide" in sys.modules:
    print("running under pyodide")
    app = App(load=True)
    app.servable()
else:
    print("running as local server")
    # we need to pass a function to create the app instead of
    # passing an already created app because the timer used in manipulate
    # requires that the server already be running
    pn.serve(
        lambda: App(load=True),
        port=9999,
        address="localhost",
        threaded=True,
        show=False
    )
    util.Browser().show("http://localhost:9999").start()
