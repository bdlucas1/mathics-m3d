#
# Courtesy ChatGPT
# provides confirmation dialog when losing unsaved changes
#

import functools
import panel as pn
import param

pn.extension("modal")


class BeforeUnloadGuard(pn.reactive.ReactiveHTML):
    """Native browser confirm on tab close/reload when dirty=True."""
    dirty = param.Boolean(default=False)

    _template = "<div></div>"

    _scripts = {
        "dirty": """
        if (!window.__pn_beforeunload_guard) {
          window.__pn_beforeunload_guard = { handler: null };
        }
        const g = window.__pn_beforeunload_guard;
        if (g.handler) {
          window.removeEventListener("beforeunload", g.handler);
          g.handler = null;
        }

        if (dirty) {
          g.handler = (e) => {
            e.preventDefault();
            e.returnValue = "";
            return "";
          };
          window.addEventListener("beforeunload", g.handler);
        }
        """
    }


class Guard(param.Parameterized):

    # parameters
    dirty = param.Boolean(default=False, doc="True if there are unsaved edits")
    message = param.String(
        default="Discard unsaved changes?",
        doc="Modal message shown when guarding an action.",
    )

    def __init__(self, **params):
        super().__init__(**params)

        self._msg = pn.pane.Markdown(self.message, margin=(0, 0, 10, 0))
        self.param.watch(self._sync_message, "message")

        self._leave_btn = pn.widgets.Button(name="Continue", button_type="danger")
        self._stay_btn  = pn.widgets.Button(name="Cancel")

        self.modal = pn.Modal(
            self._msg,
            pn.Row(self._leave_btn, pn.HSpacer(), self._stay_btn, sizing_mode="stretch_width"),
            open=False,
            show_close_button=False,
            background_close=False,
            margin=20,
        )

        self.beforeunload = BeforeUnloadGuard(dirty=self.dirty)
        self.param.watch(self._sync_dirty, "dirty")

        self._pending_action = None

        self._stay_btn.on_click(lambda *_: self._cancel())
        self._leave_btn.on_click(lambda *_: self._confirm_discard_and_run())

    def _sync_message(self, *_):
        self._msg.object = self.message

    def _sync_dirty(self, *_):
        self.beforeunload.dirty = self.dirty

    def _cancel(self):
        self._pending_action = None
        self.modal.open = False

    def _confirm_discard_and_run(self):
        self.modal.open = False
        self.dirty = False
        action = self._pending_action
        self._pending_action = None
        if action:
            action()

    def set_dirty(self, dirty):
        self.dirty = dirty

    def guard(self, action):
        """Run action now if clean; otherwise ask user and run only if confirmed."""
        if not self.dirty:
            action()
            return
        self._pending_action = action
        self.modal.open = True

    def guarded(self):
        """
        Decorator factory. Use as:

            @controller.guarded()
            def do_something(): ...

        Works for free functions and bound instance methods.
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                # capture the call (including args/kwargs) so it can be invoked later
                return self.guard(lambda: func(*args, **kwargs))
            return wrapped
        return decorator
