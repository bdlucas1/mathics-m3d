import time
import threading

import panel as pn

items = {}

def item(item, name) :
    items[name] = item
    return item

def deferred(f):
    def fun(*args, **kwargs):
        return lambda: f(*args, **kwargs)
    return fun

def delay(t):
    print("=== delaying", t)
    time.sleep(t)

@deferred
def click(name):
    print(f"=== clicking {name}")
    items[name].clicks += 1
    
@deferred
def check_text(name, expected):
    print(f"=== checking text of {name}")
    item = items[name]
    assert expected in item.text, f"item '{name}' does not have expected text '{expected}'"
    assert item.visible, f"item '{name}' is not visible" # but it is - ?

@deferred
def change_value(name, value):
    item = items[name]
    item.value = value
    item.param.trigger("value_input")

@deferred
def check_value(name, expected):
    print(f"=== checking valuet of {name}")
    item = items[name]
    assert expected in item.value, f"item '{name}' does not have expected text '{expected}'"

tests = [
    #(3, check_text("view", "")),
    #(1, click("help_button"), check_text("help", "Try it")),
    (1, click("heart_button"), 1, check_text("view", "cardioid")),
    (1, click("edit_button"), 1, check_text("edit", "cardioid")),
    (1, change_value("edit", "foobarbing")),
    (1, click("edit_button"), 1, check_text("view", "foobarbing")),
    (1, click("save_button"), 1, change_value("save_file_text_edit", "/xxx"), check_value("save_file_save_button", "Nope"))

    #(3, "file_open_button", click),
    #(3, "file_save_button", click),
]

def run_tests():
    def run_tests():
        try:
            for (*actions,) in tests:
                for action in actions:
                    if isinstance(action, (int,float)):
                        delay(action)
                    else:
                        action()
        except AssertionError as oops:
            print(f"=== FAIL: {oops}")
            return
        print("=== SUCCESS")

    threading.Thread(target=run_tests).start()
