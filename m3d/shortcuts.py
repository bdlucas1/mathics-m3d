#
# Following code is from https://github.com/holoviz/panel/issues/3193
#

from typing import TypedDict, NotRequired
from panel.custom import ReactComponent, DataEvent
import param
import panel as pn


# Note: this uses TypedDict instead of Pydantic or dataclass because Bokeh/Panel doesn't seem to
# like serializing custom classes to the frontend (and I can't figure out how to customize that).
class KeyboardShortcut(TypedDict):
    name: str
    key: str
    altKey: NotRequired[bool]
    ctrlKey: NotRequired[bool]
    metaKey: NotRequired[bool]
    shiftKey: NotRequired[bool]


class KeyboardShortcuts(ReactComponent):
    """
    Class to install global keyboard shortcuts into a Panel app.

    Pass in shortcuts as a list of KeyboardShortcut dictionaries, and then handle shortcut events in Python
    by calling `on_msg` on this component. The `name` field of the matching KeyboardShortcut will be sent as the `data`
    field in the `DataEvent`.

    Example:
    >>> shortcuts = [
        KeyboardShortcut(name="save", key="s", ctrlKey=True),
        KeyboardShortcut(name="print", key="p", ctrlKey=True),
    ]
    >>> shortcuts_component = KeyboardShortcuts(shortcuts=shortcuts)
    >>> def handle_shortcut(event: DataEvent):
            if event.data == "save":
                print("Save shortcut pressed!")
            elif event.data == "print":
                print("Print shortcut pressed!")
    >>> shortcuts_component.on_msg(handle_shortcut)
    """

    # bdl - following failed, but my change works
    #shortcuts = param.List(class_=dict)
    shortcuts = param.List()

    _esm = """
    // Hash a shortcut into a string for use in a dictionary key (booleans / null / undefined are coerced into 1 or 0)
    function hashShortcut({ key, altKey, ctrlKey, metaKey, shiftKey }) {
      return `${key}.${+!!altKey}.${+!!ctrlKey}.${+!!metaKey}.${+!!shiftKey}`;
    }

    export function render({ model }) {
      const [shortcuts] = model.useState("shortcuts");

      const keyedShortcuts = {};
      for (const shortcut of shortcuts) {
        keyedShortcuts[hashShortcut(shortcut)] = shortcut.name;
      }

      function onKeyDown(e) {
        const name = keyedShortcuts[hashShortcut(e)];
        //console.log(e, name)
        if (name) {
          e.preventDefault();
          e.stopPropagation();
          model.send_msg(name);
          return;
        }
      }

      /* bdl: I added capture:true */
      React.useEffect(() => {
        window.addEventListener('keydown', onKeyDown, {capture: true});
        return () => {
          window.removeEventListener('keydown', onKeyDown);
        };
      });

      return <></>;
    }
    """
