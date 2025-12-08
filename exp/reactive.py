import panel as pn
import param

pn.extension()

inner_panel = pn.Column(
    "# Inner panel",
    #pn.widgets.Slider(name="A slider", start=0, end=10),
    ti := pn.widgets.TextInput(name="Some text", value="foo"),
)
ti.param.watch(lambda x: print(x), "value_input")

class Wrapper(pn.reactive.ReactiveHTML):

    content = param.Parameter(precedence=-1)
    content2 = param.Parameter(precedence=-1)

    _template = """
        <div style="border: 2px solid #888; padding: 10px;">
          <h2>Wrapper ReactiveHTML</h2>
          <div id='xxx'>
            <!-- Here we embed the Panel object -->
            ${content}
            ${content2}
          </div>
        </div>
    """

#Wrapper.content2 = content = param.Parameter(precedence=-1)

print("xxx wd", Wrapper.__dict__)


# Pass the existing Panel into the ReactiveHTML instance
wrapper = Wrapper(content=inner_panel, content2="xxxcontent2")

#wrapper.servable()
wrapper.show()
