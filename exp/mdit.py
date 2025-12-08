import markdown_it
from markdown_it.presets import gfm_like
from mdit_py_plugins.dollarmath import dollarmath_plugin
from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.common.utils import escapeHtml, unescapeAll

md_text = open("ex.md").read()

# This class intercepts certain tokens - in particular, the code
# fences - in the token streak as the markdown is processed,
# and substitutes placeholders that will be where we later
# insert our Pairs that represent the editor and evaluated output for
# that code block
class MyRenderer(RendererHTML):

    def __init__(self):
        self.fence_id = 0
        self.code_blocks = []
        super().__init__()

    # Here's where we get the information for  a code block
    # ("fence" in Markdown terms), and insert a placeholder
    # which Panel will then later insert our Pair
    def fence(self, tokens, idx, options, env):
        token: Token = tokens[idx]
        info = unescapeAll(token.info).strip() if token.info else ""
        name = f"m3d_block{self.fence_id}"
        renderer.code_blocks.append((name, token.content))
        self.fence_id += 1
        return f"<div id='{name}'>${{{name}}}</div>"

md = MarkdownIt()
renderer = MyRenderer()
md.renderer = renderer
html_str = md.render(md_text)
print(html_str)

#
#
#

import panel as pn
import param

pn.extension()

# Now construct class Wrapper that inherits from ReactiveHTML.
# It defines a template, which is our rendered markdown with the
# code code_blocks replaced by parameter references, into which will
# be instantiated our Pairs.
# We have to do it indirectly by calling type(...) because
# in order to have a dynamic number of them they all have
# to be present in the original class definition because
# Panel uses a metaclass to example our Wrapper class at
# class creation time, not later at instance creation time
# I suppose they have a good reason for doing that...
class_dict = dict(_template=html_str)
for name, code in renderer.code_blocks:
    class_dict[name] = param.Parameter(precedence=-1)
Wrapper = type("Wrapper", (pn.reactive.ReactiveHTML,), class_dict)

# Now we construct the final instance which is the HTML generated
# from the markdown, with our Pairs substituted for the code blocks
args = {
    name: pn.Column(f"here is {name}") # <--- Pair goes here
    for name, _ in renderer.code_blocks
}
wrapper = Wrapper(**args)
wrapper.show()
