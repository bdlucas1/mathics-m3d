import panel as pn

class HideOnScrollColumn(pn.Column):
    """
    A Column whose first child is a toolbar that hides when scrolling down
    and reappears when scrolling up.
    """

    def __init__(
        self,
        toolbar: pn.viewable.Viewable,
        body: pn.viewable.Viewable,
        *,
        height_px: int = 48,
        hide_after_px: int = 50,
        transition_ms: int = 250,
        z_index: int = 1000,
        background: str = "white",
        border_bottom: str = "1px solid #ddd",
        fixed: bool = True,   # True: fixed to viewport, False: sticky
        **kwargs,
    ):
        pn.extension()

        cls = f"top-toolbar"
        hidden_cls = f"{cls}-hidden"
        toolbar.css_classes.append(cls)

        position = "fixed" if fixed else "sticky"
        body_pad_css = f"body{{padding-top:{height_px}px;}}" if fixed else ""

        pn.extension(raw_css=[f"""
.{cls} {{
  position: {position};
  top: 0; left: 0; right: 0;
  z-index: {z_index};
  background: {background};
  border-bottom: {border_bottom};
  transition: transform {transition_ms}ms ease-in-out;
}}
.{cls}.{hidden_cls} {{
  transform: translateY(-100%);
}}
{body_pad_css}
"""])

        toolbar_wrapped = pn.Column(
            toolbar,
            css_classes=[cls],
            sizing_mode="stretch_width",
        )

        js = pn.pane.HTML(f"""
<script>
(function () {{
  // Recursively search through light DOM + any shadow roots
  function querySelectorDeep(selector, root=document) {{
    const direct = root.querySelector?.(selector);
    if (direct) return direct;

    const nodes = root.querySelectorAll?.('*') || [];
    for (const node of nodes) {{
      if (node.shadowRoot) {{
        const found = querySelectorDeep(selector, node.shadowRoot);
        if (found) return found;
      }}
    }}
    return null;
  }}

  let lastY = window.scrollY;
  const hideAfter = {int(hide_after_px)};
  const toolbarSelector = '.{cls}';
  const hiddenClass = '{hidden_cls}';

  function init() {{
    const toolbar = querySelectorDeep(toolbarSelector, document);
    console.log("xxx search " + toolbarSelector)
    console.log("xxx found", toolbar)
    if (!toolbar) return false;

    window.addEventListener('scroll', () => {{
      console.log("xxx scolled")
      const y = window.scrollY;
      console.log("xxx to " + y)
        
      if (y > lastY && y > hideAfter) {{
        console.log("xxx adding hidden " + hiddenClass)
        toolbar.classList.add(hiddenClass);
      }} else {{
        console.log("xxx removing hidden " + hiddenClass)
        toolbar.classList.remove(hiddenClass);
      }}
      lastY = y;
    }}, {{passive: true}});

    return true;
  }}

  // Panel may render asynchronously; retry a few times
  let tries = 0;
  const maxTries = 50; // ~5s at 100ms
  const timer = setInterval(() => {{
    tries += 1;
    if (init() || tries >= maxTries) clearInterval(timer);
  }}, 100);

}})();
</script>
""")

        super().__init__(
            toolbar_wrapped,
            js,        # ensure JS runs after toolbar exists
            body,
            sizing_mode="stretch_width",
            **kwargs,
        )



import panel as pn
pn.extension()

toolbar = pn.Row(
    "A", "B"
)

content = pn.Column(
    *[
        pn.pane.Markdown(f"## Section {i}\n\n" + ("Text\n\n" * 8))
        for i in range(1, 25)
    ]
)

app = HideOnScrollColumn(
    toolbar,
    content,
    height_px=56,
    hide_after_px=80,
)

pn.serve(app)
        
