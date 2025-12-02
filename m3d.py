import sys
sys.stdout.flush()

import os
os.environ["DEMO_USE"] = "panel"
os.environ["MATHICS3_TIMING"] = "-1"

import inspect
import threading
import re

import panel as pn
import panel.widgets as pnw
import panel.io
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

pn.extension()
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

    def __init__(self, text=None, input_visible=False, run=False):
        
        self.old_expr = ""
        self.is_stale = True

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
        self.exec_button.visible = True

        # put the buttons together
        buttons = pn.Column(
            self.edit_button,
            self.exec_button,
            css_classes = ["m-button-column"]
        )

        # output
        # make initial load snappier by deferring computing the output,
        # and more importantly sending it to the browser,
        # allowing an initial view on the page while stll loading
        self.output = pn.Row(
            None, # actual output goes here
            buttons,
            css_classes = ["m-output"],
            # TODO: extract from .css file?
            styles=dict(width="fit-content", gap="1em")
        )
        def make_output():
            if run:
                self.update_if_changed()
            return self.output
        deferred_output = pn.panel(make_output, defer_load=True)

        # make us a column consisting of the input followed by the output
        # input may be invisible if not in edit mode
        super().__init__(self.input, deferred_output, css_classes=["m-pair"])


    # check whether input has changed, and eval if so
    def update_if_changed(self, force=False):
        expr = self.input.value_input
        if expr and (force or self.is_stale):
            with util.Timer("execute code block"):
                expr = fe.session.parse(expr)
                expr = expr.evaluate(fe.session.evaluation)
                layout = lt.expression_to_layout(fe, expr)
                self.output[0] = layout
            self.old_expr = expr
            self.is_stale = False
            self.exec_button.visible = False
            

class App(ui.Stack):

    def __init__(self, load, initial_mode = "view"):

        # used to make exiting edit mode faster
        self.pair_cache = {}

        # set up mode-independent stuff
        super().__init__(
            self.init_shortcuts(),
            self.init_buttons(),
            css_classes=["m-app"]
        )

        def load_view():
            self.view = pn.Column(css_classes=["m-view"])
            self.load_files(load)
            return self.view
        self.append("view", load_view)

        def load_edit():
            self.edit = pn.widgets.TextAreaInput(
                value="foo",
                visible=False,
                css_classes=["m-edit"],
                styles=dict(height="100vh"),
            )
            return self.edit
        self.append("edit", load_edit)

        def load_help():
            help = pn.Column(css_classes=["m-view"])
            self.load_m3d_file("data/help.m3d", help)
            return help
        self.append("help", load_help)

        def load_open():
            def open_file(fn):
                # TODO: new files always go into active item "view"
                # do we want to give them each their own item, with some way to switch,
                # like tabs, maybe a dropdown beside the buttons??
                self.view[:] = []
                # TODO: if I reverse the order of the following two switch doesn't work - ???
                self.load_files([fn])
                self.activate("view")
            selector = ui.open_file("data", open_file)
            return selector
        self.append("open", load_open)

        # start in requested
        # if "view" this will isntantiate the view by calling load_view via self.mode_items
        self.activate(initial_mode)


    def init_shortcuts(self):

        shortcuts = ui.KeyboardShortcuts(shortcuts=[
            ui.KeyboardShortcut(name="run", key="Enter", ctrlKey=True),
            ui.KeyboardShortcut(name="run", key="Enter", altKey=True),
            ui.KeyboardShortcut(name="run", key="Enter", metaKey=True),
            ui.KeyboardShortcut(name="run_force", key="Enter", ctrlKey=True, shiftKey=True),
            ui.KeyboardShortcut(name="run_force", key="Enter", altKey=True, shiftKey=True),
            ui.KeyboardShortcut(name="run_force", key="Enter", metaKey=True, shiftKey=True),
        ])

        def shortcut_msg(event):
            force = event.data == "run_force"
            if self.mode == "view":
                for item in self.view:
                    if isinstance(item, Pair):
                        item.update_if_changed(force=force)
            elif self.mode == "edit":
                self.toggle_mode("edit", "view")

        shortcuts.on_msg(shortcut_msg)

        return shortcuts

    # TODO: push/pop modes??
    """
    def set_mode(self, new_mode):

        if self.mode == new_mode:
            return

        # make current mode-dependent items invisible
        for item in self[self.mode_start:]:
            item.visible = False

        # lazily instantiated items
        mode_items = self.mode_items[new_mode]
        for i in range(len(mode_items)):
            mode_item = mode_items[i]
            if inspect.isfunction(mode_item):
                mode_item = mode_item()
                mode_items[i] = mode_item
                self.append(mode_item)
        
        # make new mode dependent items visible
        for item in mode_items:
            item.visible = True

        # special processing for entering or exiting edit mode
        if new_mode == "edit":
            self.enter_edit()
        if self.mode == "edit":
            self.exit_edit()

        # all ready
        self.mode = new_mode
        """

    def activate(self, mode):
        if mode == self.active_mode:
            return
        if self.active_mode == "edit":
            self.exit_edit()
        super().activate(mode)
        if mode == "edit":
            self.enter_edit()


    def toggle_mode(self, new_mode, old_mode):
        new_mode = new_mode if self.active_mode != new_mode else old_mode
        self.activate(new_mode)


    def enter_edit(self):
        def collect():
            for item in self.view:
                if isinstance(item, Pair):
                    text = item.input.value_input
                    self.pair_cache[text] = item
                    yield f"```\n{text}\n```"
                elif isinstance(item, pn.pane.Markdown):
                    yield item.object
                else:
                    assert False, "expect Pair or Markdown"
        text = "".join(collect())
        self.edit.value = text


    def exit_edit(self):
        self.view.clear()
        # value_input may be None if we haven't edited :(
        text = self.edit.value_input or self.edit.value
        self.load_m3d_string(text, self.view, run=True)
        self.pair_cache.clear()


    def init_buttons(self): 

        edit_button = ui.icon_button(
            "edit",
            "Toggle editing\nentire file",
            lambda: self.toggle_mode("edit", "view")
        )

        help_button = ui.icon_button(
            "help",
            "Help is on the way!",
            lambda: self.toggle_mode("help", "view")
        )

        file_open_button = ui.icon_button(
            "file-download",
            "Open a file",
            lambda: self.toggle_mode("open", "view")
        )

        buttons = pn.Row(
            pn.widgets.ButtonIcon(icon="file-plus"),
            file_open_button,
            pn.widgets.ButtonIcon(icon="file-download"),
            pn.widgets.ButtonIcon(icon="file-upload"),
            edit_button,
            pn.widgets.ButtonIcon(icon="player-play"),
            pn.widgets.ButtonIcon(icon="clipboard-text"),
            help_button,
            #pn.widgets.ButtonIcon(icon="mood-smile"),
            #pn.widgets.ButtonIcon(icon="mood-confuzed"),
            #pn.widgets.ButtonIcon(icon="alert-triangle"),
            #pn.widgets.ButtonIcon(icon="square-x"),
            #pn.widgets.ButtonIcon(icon="heart"),
            #pn.widgets.ButtonIcon(icon="file-pencil"),    
            #pn.widgets.ButtonIcon(icon="player-track-next"),
            css_classes=["m-button-row"]
        )

        return buttons


    def load_m3d_file(self, md_fn, into, run=True):
        print("loading", md_fn)
        md_str = open(md_fn).read()
        # TODO: autorun optional?
        self.load_m3d_string(md_str, into, run=run)


    def load_m3d_string(self, md_str, into, run=False):

        # TODO: allow for tags or instructions after ``` until end of line
        md_parts = re.split("(```)", md_str)
        is_m3 = False

        for part in md_parts:

            if part == "```":
                is_m3 = not is_m3

            elif is_m3:

                # construct the pair, consulting the cache that may have been
                # left when we entered edit mode
                text = part.strip()
                try:
                    pair = self.pair_cache[text]
                    print("USING CACHED PAIR")
                    del self.pair_cache[text]
                except KeyError:
                    pair = Pair(text, input_visible = not run, run = run)

                into.append(pair)

            else:

                # render the text using Markdown
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
                        h1 {font-size: 20pt; margin-top: 2.0em; &:first-child {margin-top: 0em;}}
                        h2 {font-size: 18pt; margin-top: 1.6em; &:first-child {margin-top: 0em;}}
                        h3 {font-size: 16pt; margin-top: 1.2em; &:first-child {margin-top: 0em;}}
                        h4 {font-size: 14pt; margin-top: 0.8em; &:first-child {margin-top: 0em;}}
                    """]
                )
                into.append(md)



    def load_m(self, m_fn):
        m_str = open(m_fn).read()    
        pair = Pair(m_str.strip(), run=True)
        self.view.append(pair)


    def load_files(self, fns):
        if len(fns):
            for fn in fns:
                if fn.endswith(".m3d"):                   
                    self.load_m3d_file(fn, self.view)
                elif fn.endswith(".m"):
                    self.load_m(fn)
                else:
                    print(f"Don't understand file {fn}")
        else:
            self.view.append(Pair(None, input_visible=True))



#
# startup action depends on mode -
# building for pyodide, running under pyodide, or running as a server
#

if "DEMO_BUILD_PYODIDE" in os.environ:

    print("building for pyodide")
    app = App(load=[])
    app.servable()


elif "pyodide" in sys.modules:

    print("running under pyodide")
    app = App(load=["data/gallery.m3d"])
    app.servable()

else:
    print("running as local server")

    import argparse
    parser = argparse.ArgumentParser(description="m3d")
    parser.add_argument(
        "--initial-mode", "-i",
        choices=["view","edit","help","open","save"],
        default="view"
    )
    parser.add_argument("files", nargs="*", type=str)
    args = parser.parse_args()

    # we need to pass a function to create the app instead of
    # passing an already created app because the timer used in manipulate
    # requires that the server already be running
    app = App(load=args.files, initial_mode=args.initial_mode) # sliders don't work in this mode
    #app = lambda: App(load=args.files, initial_mode=args.initial_mode)

    pn.serve(
        app,
        port=9999,
        address="localhost",
        threaded=True,
        show=False
    )
    util.Browser().show("http://localhost:9999").start()
