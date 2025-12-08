import panel as pn
import param

pn.extension()

def make_wrapper():

    class_dict = dict(
        slot1 = param.Parameter(precedence=-1),
        slot2 = param.Parameter(precedence=-1),
        _template = """
            <div id="slot1">${slot1}</div>
            <div id="slot2">${slot2}</div>
        """
    )

    # Create a new ReactiveHTML subclass
    return type("Wrapper", (pn.reactive.ReactiveHTML,), class_dict)

Wrapper = make_wrapper()

wrapper = Wrapper(slot1="hoho1", slot2="hoho2")
#wrapper.slot1 = "fffo1"
#wrapper.slot2 = "fffo2"

wrapper.show()
