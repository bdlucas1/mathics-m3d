import yaml
import collections

fn = "/Users/bdlucas1/mathics-core/test/builtin/drawing/doc_tests.yaml"
tests = yaml.safe_load(open(fn))

files = {}

for name, info in tests.items():
    expr = info["expr"]
    fun = expr.split("[")[0]
    print(name, fun, expr)
    if fun not in files:
        files[fun] = open("doc-" + fun.lower() + ".m3d", "w")
    print(f"``` m3d test={name}\n{expr}\n```\n", file=files[fun])
