import inspect
import threading
import re
import sys
import pathlib
import itertools

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
import shortcuts
import hider

test = None

pn.extension()
pn.extension('plotly')
pn.extension('mathjax')

#help(pn.config)
#'<meta name="viewport" content="width=device-width; initial-scale=1.0; maximum-scale=5.0; user-scalable=1;" />'

import mathics.builtin.drawing.plot
mathics.builtin.drawing.plot.use_vectorized_plot = True

#
# An input-output pair, as a column
#

class Pair(pn.Column):

    def __init__(self, top, text=None, input_visible=False, run=False, test_info=None):
        
        self.top = top
        self.old_expr = ""
        self.is_stale = True
        self.opener = "```"
        self.test_info = test_info

        # actual loading and therefore testing is deferred;
        # track pending so we know when we're done
        if test_info:
            test.pending()

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
    def update(self, expr=None):
        try:

            expr_str = self.input.value_input
            self.old_expr = expr_str
            session = self.top.session
            
            # evaluate it if not provided (e.g. from shell)
            if not expr:
                session.evaluation.out.clear()
                #expr = session.parse(expr)
                expr = session.evaluate(expr_str)

            if expr is None:
                # TODO: is this the right behavior?
                self.output[0] = "None"
            else:
                # contruct layout from expr
                layout = lt.expression_to_layout(self.top, expr)

                # either show it to user, or pass it to test
                # can't do both because test "layout" mode requires
                # that sole ownership of the layout to save it to image
                if self.test_info:
                    test.test(self.test_info, layout, expr)
                else:
                    self.output[0] = layout

            # update state
            self.is_stale = False
            self.exec_button.visible = False

        except (Exception, core.AbortInterrupt) as oops:
            if isinstance(oops, core.InvalidSyntaxError): kind = "Syntax error"
            elif isinstance(oops, core.IncompleteSyntaxError): kind = "Syntax error"
            elif isinstance(oops, core.SyntaxError): kind = "Syntax error"
            elif isinstance(oops, NotImplementedError): kind = "Not implemented"
            elif isinstance(oops, core.AbortInterrupt): kind = "Abort"
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

        except SystemExit:
            print("bye")
            os._exit(0)

        finally:
            self.messages.clear()
            for o in session.evaluation.out:
                msg = pn.widgets.StaticText(
                    value=o.text,
                    styles=dict(padding="0.5em")
                )
                print(msg)
                self.messages.append(msg)

        
class View(pn.Column):
    """
    Displays the page as alternating parts of Markdown and
    and Pair, where each Pair has code (input) and the result 
    of evaluating that code (output)
    """

    persistent = True
    pair_cache = {}

    def __init__(self, top, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.top = top
        self.current_fn = None

    @property
    def text(self):
        """
        Reconstruct the markdown for the entire page by
        concatenating the text for the Pair and Markdown elements
        that constitute the View
        """
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
        if fns is None:
            # completely empty view is requested
            # TODO: subsequent append doesn't work without the following - ?
            self.append("")
        elif len(fns):
            # load some files
            self.current_fn = fns[0]
            for fn in fns:
                if fn.endswith(".m3d") or fn.endswith(".md"):
                    self.load_m3d_file(fn, run, show_code)
                elif fn.endswith(".m"):
                    self.load_m(fn)
                else:
                    print(f"Don't understand file {fn}")
        else:
            # fns is [], so create a blank Pair to start
            self.append(Pair(self.top, None, input_visible=True))


    def load_m3d_file(self, md_fn, run, show_code=False):
        print("loading", md_fn)
        md_str = open(md_fn).read()
        self.load_m3d_string(md_str, run, show_code, fn=md_fn)


    def load_m3d_string(self, md_str, run, show_code=False, fn=None):
        """ Load a Mathics3+Markdown (.m3d) document given as a string """

        # split the document at fence (lines beginning with ```) boundaries
        # the output of re.split includes the delimiters, i.e. the fence lines
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

                # it's a fence, so toggle the mode flag, parse the remainder
                # of the line as options, and remember the opening fence
                # so we can reconstruct it later when we need to go
                # recover markdown text for the whole page
                is_m3 = not is_m3
                options = global_options | parse_options(part)
                opener = part

            elif is_m3:

                # this part is a code block, so  construct the pair, consulting
                # the cache that may have been left when we entered edit mode
                text = part.strip()
                try:
                    pair = self.pair_cache[text]
                    print("USING CACHED PAIR")
                    del self.pair_cache[text]

                except KeyError:
                    
                    # override global autorun
                    autorun = truthful(options.get("autorun", run))

                    # remember options to past to test if there is a "test" option
                    test_info = None
                    if test and "test" in options:
                        test_info = options
                        test_info["fn"] = fn

                    # option to show the code for this part
                    input_visible = show_code or not autorun

                    # construct the pair
                    pair = Pair(
                        self.top,
                        text,
                        input_visible=input_visible,
                        run=autorun,
                        test_info=test_info
                    )

                pair.opener = opener
                self.append(pair)

            else:

                # global options can also be found in comments
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
                        p + p {
                            margin-top: 1em;
                        }
                        em {
                            font-style: italic;
                        }
                        h1 {font-size: 20pt; margin-top: 2.5em; &:first-child {margin-top: 0em;}}
                        h2 {font-size: 18pt; margin-top: 1.6em; &:first-child {margin-top: 0em;}}
                        h3 {font-size: 16pt; margin-top: 1.2em; &:first-child {margin-top: 0em;}}
                        h4 {font-size: 14pt; margin-top: 0.8em; &:first-child {margin-top: 0em;}}
                    """]
                )
                self.append(md)


    def load_m(self, m_fn):
        """ Load a .m file that contains only a Mathics3 formula """
        m_str = open(m_fn).read()    
        # TODO: not sure following is right
        test_info = dict(fn=m_fn) if test else None
        pair = Pair(self.top, m_str.strip(), run=True, test_info=test_info)
        self.append(pair)

    def update_all_changed(self, force=False):
        for item in self:
            if isinstance(item, Pair):
                item.update_if_changed(force=force)



class Edit(pn.widgets.TextAreaInput):
    """ Used in edit mode to display the entire file as text for editing """

    # persists even between UI mode changes
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



class ButtonBar(pn.Row):

    def __init__(self, app):

        # used to change icon when activated or inactivated
        self.mode_buttons = {}

        # buttons that switch mode and have different styling to indicate current mode
        def mode_button(mode, icon, tip, test_name):
            button = ui.icon_button(
                icon=icon,
                tip=tip,
                on_click=lambda: app.top.toggle_mode(mode, "view")
            )
            test_ui.item(button, test_name)
            mode_button = pn.Row(button, css_classes=["m-mode-button"])
            self.mode_buttons[mode] = mode_button
            return mode_button
            
        # button that just performs an action without switching mode
        def action_button(icon, tip, on_click, test_name):
            button = ui.icon_button(icon, tip, on_click)
            test_ui.item(button, test_name)
            return button

        # create new document action
        new_button = action_button(
            icon="square-plus",
            tip="New document",
            on_click=lambda: app.top.view.load_files([], False),
            test_name="new_button",
        )

        # go into "edit" mode to edit entire document
        edit_button = mode_button(
            mode="edit",
            icon="edit",
            tip="Toggle editing\nentire file",
            test_name="edit_button",
        )

        # reload document action
        def reload():
            # TODO: mode? cache?
            app.top.activate("view")
            if app.top.view.current_fn:
                app.top.view.load_files([app.top.view.current_fn], run=True, show_code=False)
        reload_button = action_button(
            icon="reload",
            tip="Reload current file",
            on_click=reload,
            test_name="reload_button",
        )

        # execute action, TBD exactly what - all? changed?
        def play():
            print("TBD")
        play_button = action_button(
            icon="player-play",
            tip="TBD",
            on_click=play,
            test_name="play_button",
        )

        # TODO: this will actually be a mode button, I think
        def log():
            print("TBD")
        log_button = action_button(
            icon="clipboard-text",
            tip="TBD",
            on_click=log,
            test_name="log_button",
        )

        # go into "help" mode
        help_button = mode_button(
            mode="help",
            icon="help",
            tip="Help is on the way!",
            test_name="help_button",
        )

        # go into "open" mode to open a file
        file_open_button = mode_button(
            mode="open",
            icon="download",
            tip="Open a file",
            test_name="file_open_button",
        )

        # go into "save" mode t save a file
        file_save_button = mode_button(
            mode="save",
            icon="upload",
            tip="Save file",
            test_name="file_save_button",
        )

        # like it action
        def load_and_activate(fns, run):
            app.top.view.load_files(fns, run)
            app.top.activate("view")
        heart_button = action_button(
            icon="heart",
            tip="Like it?",
            on_click=lambda: load_and_activate([util.resource("data/cardio.m3d")], True),
            test_name="heart_button",
        )

        super().__init__(
            new_button,
            file_open_button,
            file_save_button,
            edit_button,
            reload_button,
            play_button,
            log_button,
            help_button,
            heart_button,
            #pn.widgets.ButtonIcon(icon="mood-smile"),
            #pn.widgets.ButtonIcon(icon="mood-confuzed"),
            #pn.widgets.ButtonIcon(icon="alert-triangle"),
            #pn.widgets.ButtonIcon(icon="square-x"),
            #pn.widgets.ButtonIcon(icon="file-pencil"),    
            #pn.widgets.ButtonIcon(icon="player-track-next"),
            css_classes=["m-button-row"]
        )

    def activate_button(self, new_mode):
        for mode, button in self.mode_buttons.items():
            active_cls = "m-active"
            if new_mode == mode:
                button.css_classes.append(active_cls)
            elif active_cls in button.css_classes:
                button.css_classes.remove(active_cls)
            button.param.trigger('css_classes')


class Shortcuts(shortcuts.KeyboardShortcuts):

    def __init__(self, top):

        super().__init__(shortcuts=[
            shortcuts.KeyboardShortcut(name="run", key="Enter", ctrlKey=True),
            shortcuts.KeyboardShortcut(name="run", key="Enter", altKey=True),
            shortcuts.KeyboardShortcut(name="run", key="Enter", metaKey=True),
            shortcuts.KeyboardShortcut(name="run_force", key="Enter", ctrlKey=True, shiftKey=True),
            shortcuts.KeyboardShortcut(name="run_force", key="Enter", altKey=True, shiftKey=True),
            shortcuts.KeyboardShortcut(name="run_force", key="Enter", metaKey=True, shiftKey=True),
        ])

        def shortcut_msg(event):
            force = event.data == "run_force"
            if top.active_mode == "view":
                top.view.update_all_changed()
            elif top.active_mode == "edit":
                top.toggle_mode("edit", "view")

        self.on_msg(shortcut_msg)



# TODO: everything called .app or app. or app- should be renamed top
class Top(ui.Stack):
    """
    The top-level is a Stack, which is a Column that manages mode switching
    by instantiating and controling the visibility of its constituents
    """

    def __init__(
            self,
            app,
            load=[],
            initial_mode="view",
            autorun=True,
            show_code=False,
            test_ui_run=False,
            session=None,
    ):

        self.session = session or core.MathicsSession()
        self.app = app
        self.active_mode = None
        self.text_owner = None

        # set up mode-independent stuff
        super().__init__(
            Shortcuts(self),
            #ButtonBar(self), moved to App
            css_classes=["m-top"]
        )

        # "view" mode: show the m3d file
        def make_view():
            self.view = View(self, css_classes=["m-view"])
            test_ui.item(self.view, "view")
            self.view.load_files(load, run=autorun, show_code=show_code)
            return self.view
        self.append("view", make_view)

        # "edit" mode: edit the whole m3d file
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

        # "help" mode: show m3d help
        def make_help():
            help = View(self, css_classes=["m-view"])
            help.load_m3d_file(util.resource("data/help.m3d"), run=True)
            test_ui.item(help, "help")
            return help
        self.append("help", make_help)

        data_root = util.resource("data")

        # "open" mode: show the open file dialog
        def make_open():
            # TODO: new files always go into active item "view"
            # do we want to give them each their own item, with some way to switch,
            # like tabs, maybe a dropdown beside the buttons??
            def on_open(fn):
                self.view.load_files([fn], run=autorun)
                self.activate("view")
            return Open(data_root, on_open)
        self.append("open", make_open)

        # "save" mode: show the save file dialog
        def make_save():
            text = self.text_owner.text
            def on_save(fn):
                print(f"saving to {fn}")
                if os.path.exists(fn):
                    with open(fn) as f, open(fn+"~", "w") as t:
                        t.write(f.read())
                with open(fn, "w") as f:
                    f.write(text)
                self.activate("view")
            return Save(self.view.current_fn, data_root, on_save)
        self.append("save", make_save)


        # start in requested mode
        # if "view" this will isntantiate the view by
        # calling make_view via self.active_mode_items
        self.activate(initial_mode)

        # start tests after we're loaded
        if test_ui_run:
            pn.state.onload(test_ui.run_tests, threaded=True)


    def toggle_mode(self, new_mode, old_mode):
        new_mode = new_mode if self.active_mode != new_mode else old_mode
        self.activate(new_mode)


    def activate(self, new_mode):

        old_mode = self.active_mode
        if new_mode == old_mode:
            return

        # we've moving away from old_mode (previous test guaranteed that)
        # not persistent means it has state that must be renewed next time it's opened
        if self.active_item and not self.active_item.persistent:
            self.close_item(self.active_item)

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

        # indicate mode in toolbar
        self.app.buttons.activate_button(new_mode)


    def append_evaluated_pair(self, text, expr):
        pair = Pair(self, text=text.strip(), run=True, input_visible=True)
        self.view.append(pair)
        pair.update(expr)


class App(hider.Hider):

    def __init__(self, **kwargs):

        self.buttons = ButtonBar(self)
        self.top = Top(self, **kwargs);

        super().__init__(
            self.buttons,
            self.top,
            hide_after_px=50,
            fixed=False
        )

    # TODO when App was moved up a level so that what was App is now Top
    # which is contained in the new App, had to add this delegation method,
    # which is an external API (used by shell). Also had to use **kwards
    # to init Top. So seems exposing a class in the API is a bit fragile -
    # is there a better pattern? Maybe just expose free functions to completely hide
    # class structure? Can't inherit from Top as it's the Hider that needs to be served.
    def append_evaluated_pair(self, text, expr):
        self.top.append_evaluated_pair(text, expr)

