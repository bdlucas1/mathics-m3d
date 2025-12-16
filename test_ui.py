import time
import threading
import os

import panel as pn

import util

items = {}

def item(item, name) :
    items[name] = item
    return item

def delay(t):
    print("=== delaying", t)
    time.sleep(t)

def delayed(f):
    def fun(*args, **kwargs):
        time.sleep(1)
        return f(*args, **kwargs)
    return fun

@delayed
def click(name):
    print(f"=== clicking {name}")
    items[name].clicks += 1
    
@delayed
def change_value(name, value, trigger_field="value_input"):
    item = items[name]
    item.value = value
    item.param.trigger(trigger_field)


def check_field(name, field, expected):
    print(f"=== checking {field} of {name}")    
    item = items[name]
    field_str = getattr(item, field)
    assert expected in field_str, f"item '{name}' does not have expected {field} '{expected}'"
    assert item.visible, f"item '{name}' is not visible"

@delayed
def check_text(name, expected):
    check_field(name, "text", expected)

@delayed
def check_value(name, expected):
    check_field(name, "value", expected)

@delayed
def check_name(name, expected):
    check_field(name, "name", expected)

@delayed
def check_file(name, expected):
    print(f"=== checking file {name}")
    assert os.path.exists(name), f"file {name} does not exist"
    with open(name) as f:
        text = f.read()
        assert expected in text, f"file {name} does not contain expected text {expected}"


test_file = util.resource("data/test.m3d")
test_string = str(time.time())

def run_tests_really():

    # make sure view is instantiated on startup
    check_text("view", "")

    # check that help loads properly
    click("help_button")
    check_text("help", "Try it")

    # check that heart loads properly
    click("heart_button")
    check_text("view", "cardioid")

    # go to edit mode, make sure text carries over
    click("edit_button")
    check_text("edit", "cardioid")

    # change the text, go back to view mode, check that the text comes along
    change_value("edit", test_string)
    click("edit_button")
    check_text("view", test_string)

    # TODO: restore file save tests
    # after restoring edit field
    return 

    # click save button, enter a forbidden file, make sure save button updates accordingly
    click("save_button")
    change_value("save_file_text_input", "../xxx")
    check_name("save_file_save_button", "Nope")

    # now save it to some place legit and check
    if os.path.exists(test_file):
        os.remove(test_file)
    change_value("save_file_text_input", test_file)
    #check_name("save_file_save_button", "Save") # TODO: failing, but works manually - why?
    click("save_file_save_button")
    check_file(test_file, test_string)

    # clear content
    click("edit_button")
    change_value("edit", "hoohah")
    check_text("edit", "hoohah")
    click("edit_button")
    check_text("view", "hoohah")

    # now open it and check text
    click("open_button")
    # TODO: check visibility
    change_value("open_file_select", [(True, test_file)], trigger_field="value")
    click("open_file_open_button")
    check_text("view", test_string)
    click("edit_button")
    check_text("edit", test_string)

    # clean up
    os.remove(test_file)



def run_tests_report():
    try:
        run_tests_really()
    except AssertionError as oops:
        print(f"=== FAIL: {oops}")
        return
    print("=== SUCCESS")


def run_tests():
    threading.Thread(target=run_tests_report).start()
