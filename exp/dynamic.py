import panel as pn
import param

pn.extension()

def make_wrapper():

    # Build parameter definitions
    params = dict(
        slot1 = param.Parameter(precedence=-1),
        slot2 = param.Parameter(precedence=-1),
    )

    template = """
        <div id="foo">xxxslot1 ${slot1}</div>
        <div id="bar">xxxslot2 ${slot2}</div>
    """

    class_dict = {
        **params,
        "_template": template,
    }

    # Create a new ReactiveHTML subclass
    return type("DynamicWrapper", (pn.reactive.ReactiveHTML,), class_dict)

DynamicWrapper = make_wrapper()

wrapper = DynamicWrapper(slot1="hoho1", slot2="hoho2")
#wrapper.slot1 = "fffo1"
#wrapper.slot2 = "fffo2"

wrapper.show()
