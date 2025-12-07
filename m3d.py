import sys
sys.stdout.flush()

import os
os.environ["DEMO_USE"] = "panel"
if not "MATHICS3_TIMING" in os.environ:
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
import test_ui

pn.extension()
pn.extension('plotly')
pn.extension('mathjax')
pn.extension(raw_css=[open('m3d.css').read()])

class FE:
    def __init__(self):
        self.session = core.MathicsSession()
        self.test_mode = False

fe = FE()


#
# An input-output pair, as a column
#

class Pair(pn.Column):

    def __init__(self, text=None, input_visible=False, run=False, test_fn=None):
        
        self.old_expr = ""
        self.is_stale = True
        self.opener = "```"
        self.test_fn = test_fn

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

        # messages
        self.messages = pn.Column(
            styles=dict(background="#fff0f0")
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
        super().__init__(self.input, self.messages, deferred_output, css_classes=["m-pair"])


    # check whether input has changed, and eval if so
    def update_if_changed(self, force=False):
        expr = self.input.value_input
        if expr and (force or self.is_stale):
            self.update()

    @util.Timer("execute code block")
    def update(self):
        try:
            expr = self.input.value_input
            self.old_expr = expr
            fe.session.evaluation.out.clear()
            expr = fe.session.parse(expr)
            if not expr:
                self.input.visible = True
                return
            layout = lt.expression_to_layout(fe, expr)
            if self.test_fn:
                import test2 # does stuff on import so, ...
                test2.test(self.test_fn, layout)
            self.output[0] = layout
            self.is_stale = False
            self.exec_button.visible = False
        except Exception as oops:
            if isinstance(oops, core.InvalidSyntaxError): kind = "Syntax error"
            elif isinstance(oops, core.IncompleteSyntaxError): kind = "Syntax error"
            elif isinstance(oops, core.SyntaxError): kind = "Syntax error"
            elif isinstance(oops, NotImplementedError): kind = "Not implemented"
            else: kind = "Internal error"
            msg = f"{kind}: {oops}"
            print(msg)
            util.print_exc_reversed()
            error_box = pn.widgets.StaticText(
                value=msg,
                styles = dict(
                    background = "#fff0f0",
                    padding = "0.5em"
                )
            )
            self.output[0] = error_box
        finally:
            self.messages.clear()
            for o in fe.session.evaluation.out:
                msg = pn.widgets.StaticText(
                    value=o.text,
                    styles=dict(padding="0.5em")
                )
                print(msg)
                self.messages.append(msg)

        
class View(pn.Column):

    persistent = True
    pair_cache = {}

    @property
    def text(self):
        def collect():
            for item in self:
                if isinstance(item, Pair):
                    text = item.input.value_input or item.input.value
                    self.pair_cache[text] = item
                    yield f"{item.opener}\n{text}\n```"
                elif isinstance(item, pn.pane.Markdown):
                    yield item.object
                else:
                    assert False, "expect Pair or Markdown"
        text = "".join(collect())
        return text
    
    @text.setter
    def text(self, text):
        self.clear()
        self.load_m3d_string(text, run=False)
        self.pair_cache.clear()


    def load_files(self, fns, run, show_code=False):
        self[:] = []
        if len(fns):
            for fn in fns:
                if fn.endswith(".m3d") or fn.endswith(".md"):
                    self.load_m3d_file(fn, run, show_code)
                elif fn.endswith(".m"):
                    self.load_m(fn)
                else:
                    print(f"Don't understand file {fn}")
            if len(fns) == 1:
                self.current_fn = fns[0]
        else:
            self.append(Pair(None, input_visible=True))


    def load_m3d_file(self, md_fn, run, show_code=False):
        print("loading", md_fn)
        md_str = open(md_fn).read()
        self.load_m3d_string(md_str, run, show_code, fn=md_fn)


    def load_m3d_string(self, md_str, run, show_code=False, fn=None):

        # TODO: allow for tags or instructions after ``` until end of line
        md_parts = re.split("(```[^\n]*)", md_str)
        is_m3 = False

        def parse_options(s):
            options = {}
            if "m3d" in s:
                for nv in s.split():
                    nv = nv.split(":")
                    if len(nv) == 2:
                        options[nv[0]] = nv[1]
            return options
                        
        def truthful(x):
            return str(x).lower() in ("true", "on", "yes")

        global_options = {}

        for part in md_parts:

            if part.startswith("```"):
                opener = part
                options = global_options | parse_options(part)
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
                    
                    # override global autorun
                    autorun = truthful(options.get("autorun", run))

                    # construct test file basename if this part has a test:<part> option
                    test_fn = None
                    if fe.test_mode and fn:
                        if test_part := options.get("test", None):
                            base_fn, _ = os.path.splitext(fn)
                            # = sorts after .
                            test_fn = f"{base_fn}={test_part}"

                    # option to show the code for this part
                    input_visible = show_code or not autorun

                    # construct the pair
                    pair = Pair(text, input_visible=input_visible, run=autorun, test_fn=test_fn)

                pair.opener = opener
                self.append(pair)

            else:

                for comment in re.findall("<!--[\\s\\S]*?-->", part):
                    global_options |= parse_options(comment)

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
                self.append(md)


    def load_m(self, m_fn):
        m_str = open(m_fn).read()    
        pair = Pair(m_str.strip(), run=True)
        self.append(pair)

    def update_all_changed(self, force=False):
        for item in self:
            if isinstance(item, Pair):
                item.update_if_changed(force=force)



class Edit(pn.widgets.TextAreaInput):

    persistent = True

    @property
    def text(self):
        return self.value_input or self.value

    @text.setter
    def text(self, text):
        self.value = text


class Open(ui.OpenFile):
    persistent = True


class Save(ui.SaveFile):
    persistent = False


class App(ui.Stack):

    def __init__(self, load, initial_mode = "view", autorun=True, show_code=False):

        self.current_fn = None
        self.active_mode = None
        self.text_owner = None

        # set up mode-independent stuff
        super().__init__(
            self.init_shortcuts(),
            self.init_buttons(),
            css_classes=["m-app"]
        )

        def make_view():
            self.view = View(css_classes=["m-view"])
            test_ui.item(self.view, "view")
            self.view.load_files(load, run=autorun, show_code=show_code)
            return self.view
        self.append("view", make_view)

        def make_edit():
            self.edit = Edit(
                value="foo",
                visible=False,
                css_classes=["m-edit"],
                styles=dict(height="100vh"),
            )
            test_ui.item(self.edit, "edit")
            return self.edit
        self.append("edit", make_edit)

        def make_help():
            help = View(css_classes=["m-view"])
            help.load_m3d_file("data/help.m3d", run=True)
            test_ui.item(help, "help")
            return help
        self.append("help", make_help)

        data_root = "data"

        def make_open():
            # TODO: new files always go into active item "view"
            # do we want to give them each their own item, with some way to switch,
            # like tabs, maybe a dropdown beside the buttons??
            def on_open(fn):
                self.view.load_files([fn], run=autorun)
                self.activate("view")
            return Open(data_root, on_open)
        self.append("open", make_open)

        def make_save():
            text = self.text_owner.text
            def on_save(fn):
                if os.path.exists(fn):
                    with open(fn) as f, open(fn+"~", "w") as t:
                        t.write(f.read())
                with open(fn, "w") as f:
                    f.write(text)
                self.activate("view")
            return Save(self.current_fn, data_root, on_save)
        self.append("save", make_save)


        # start in requested mode
        # if "view" this will isntantiate the view by
        # calling make_view via self.active_mode_items
        self.activate(initial_mode)

        # start tests after we're loaded
        # TODO: command-line flag
        #pn.state.onload(test_ui.run_tests, threaded=True)


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
            if self.active_mode == "view":
                self.view.update_all_changed()
            elif self.active_mode == "edit":
                self.toggle_mode("edit", "view")

        shortcuts.on_msg(shortcut_msg)

        return shortcuts


    def toggle_mode(self, new_mode, old_mode):
        new_mode = new_mode if self.active_mode != new_mode else old_mode
        self.activate(new_mode)


    def activate(self, new_mode):

        old_mode = self.active_mode
        if new_mode == old_mode:
            return

        # we've moving away from old_mode (previous test guaranteed that)
        # not persistent means it has state that must be renewed next time it's opened
        #if self.active_item and not self.active_item.persistent:
        #    self.close_item(self.active_item)

        # sets the new mode, and may instantiate associated ui artifacts
        # so we have to do this before we can handle any transition logic
        super().activate(new_mode)

        # with the UI artifacts in place, we can handle transition logic,
        # in particular transfer active text from old to new owner if necessary
        if self.text_owner and new_mode == "view" and self.text_owner is not self.view:
            self.view.text = self.text_owner.text
        if self.text_owner and new_mode == "edit"  and self.text_owner is not self.edit:
            self.edit.text = self.text_owner.text
        if new_mode == "edit":
            self.text_owner = self.edit
        if new_mode == "view":
            self.text_owner = self.view


    def get_current_text(self):
        print("get_current_text owner", self.text_owner)
        if self.text_owner == "edit":
            return self.get_edit_text()
        elif self.text_owner == "view":
            return self.get_view_text()


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
            "download",
            "Open a file",
            lambda: self.toggle_mode("open", "view")
        )

        file_save_button = ui.icon_button(
            "upload",
            "Save file",
            lambda: self.toggle_mode("save", "view")
        )

        def load_and_activate(fns, run):
            self.view.load_files(fns, run)
            self.activate("view")
        heart_button = ui.icon_button(
            "heart",
            "Like it?",
            lambda: load_and_activate(["data/cardio.m3d"], True)
        )

        buttons = pn.Row(
            pn.widgets.ButtonIcon(icon="square-plus"),
            test_ui.item(file_open_button, "open_button"),
            test_ui.item(file_save_button, "save_button"),
            test_ui.item(edit_button, "edit_button"),
            pn.widgets.ButtonIcon(icon="player-play"),
            pn.widgets.ButtonIcon(icon="clipboard-text"),
            test_ui.item(help_button, "help_button"),
            test_ui.item(heart_button, "heart_button"),
            #pn.widgets.ButtonIcon(icon="mood-smile"),
            #pn.widgets.ButtonIcon(icon="mood-confuzed"),
            #pn.widgets.ButtonIcon(icon="alert-triangle"),
            #pn.widgets.ButtonIcon(icon="square-x"),
            #pn.widgets.ButtonIcon(icon="file-pencil"),    
            #pn.widgets.ButtonIcon(icon="player-track-next"),
            css_classes=["m-button-row"]
        )

        return buttons



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
    app = App(load=["data/help.m3d"])
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
    parser.add_argument("--no-autorun", action="store_true")
    parser.add_argument("--show-code", action="store_true")        
    parser.add_argument("--test", action="store_true")
    parser.add_argument("files", nargs="*", type=str)
    args = parser.parse_args()
    fe.test_mode = args.test

    app = App(
        load=args.files,
        initial_mode=args.initial_mode,
        show_code=args.show_code,
        autorun=not args.no_autorun
    )
    title =  " ".join(["Markdown+Mathics3", *args.files])
    util.show(app, title)

