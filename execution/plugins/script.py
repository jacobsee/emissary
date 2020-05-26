from jinja2 import Template

code_template = Template("""
def fn(params):
    {{ code_inject|indent(width=4) }}
""")


def process(context, params):

    if "script" in params and "script_file" in params:
        print("Cannot process script and script_file in the same block - please separate them.")
        raise Exception

    if "script" in params:
        code = code_template.render(code_inject=params["script"])
        local_vars = dict(locals())
        exec(code, local_vars)
        result = local_vars["fn"](params)
        return result
