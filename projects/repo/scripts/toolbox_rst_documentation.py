import yaml
import pathlib
import sys
import logging

import fire.inspectutils
import fire.docstrings

SCRIPT_THIS_DIR = pathlib.Path(__file__).absolute().parent
PROJECT_DIR = SCRIPT_THIS_DIR.parent
TOPSAIL_DIR = SCRIPT_THIS_DIR.parent.parent.parent

def _generate_config(component):
    doc = fire.docstrings.parse(component.__doc__)
    spec = fire.inspectutils.GetFullArgSpec(component)
    args_with_no_defaults = spec.args[:len(spec.args) - len(spec.defaults)]
    args_with_defaults = spec.args[len(spec.args) - len(spec.defaults):]
    args_defaults = dict(zip(args_with_defaults, spec.defaults))

    args = {}
    for arg in doc.args or {}:
        args[arg.name] = arg

    ansible_mapped_params = getattr(component, "ansible_mapped_params", False)

    ansible_constants = getattr(component, "ansible_constants", [])

    func_name = component.__func__.__qualname__ if hasattr(component, "ansible_role") \
        else component.__qualname__

    dest = TOPSAIL_DIR / "docs" / "toolbox.generated" / (func_name + ".rst")

    dest.parent.mkdir(parents=True, exist_ok=True)
    logging.info(f"{component.__qualname__}")
    logging.info(f"- generating {dest} ...\n")
    command_name = func_name.replace(".", " ").lower()

    with open(dest, "w") as f:
        print(f"""\
:orphan:

..
    _Auto-generated file, do not edit manually ...
    _Toolbox generate command: {' '.join(sys.argv[1:])}
    _ Source component: {component.__qualname__}


{command_name}
{len(command_name)*'='}

{(doc.summary or "").replace("`", "``")}

{doc.description or ""}
""", file=f)

        mapped_params = args_with_no_defaults + args_with_defaults

        if len(mapped_params) > 0:
            print("""
Parameters
----------

""", file=f)


        for i, arg in enumerate(mapped_params):
            try:
                description = args[arg].description
                description = description[0].upper() + description[1:]
            except KeyError:
                description = f"Missing documentation for {arg}"

            print(f"``{arg}``  \n\n* {description}", file=f)

            try:
                print(f"* type: {spec.annotations[arg].__name__.title()}", file=f)
            except KeyError:
                # no type annotation, ignore
                pass

            if args_defaults.get(arg):
                default_value = args_defaults[arg]
                NL = "\n"; NL_ESC = "\\n" # f-string expression part cannot include a backslash
                print(f"\n* default value: ``{str(default_value).replace(NL, NL_ESC)}``", file=f)

            print(f"", file=f)

            if i < len(mapped_params)-1:
                print("", file=f)

        if len(ansible_constants) > 0:
            print("", file=f)
            print("# Constants", file=f)

        for i, constant in enumerate(ansible_constants):
            print(f"# {constant['description']}", file=f)
            print(f"# Defined as a constant in {component.__qualname__}", file=f)
            print(yaml.dump({f"{component.ansible_role}_{constant['name']}": constant["value"]}).strip(), file=f)
            if i < len(ansible_constants)-1:
                print("", file=f)

def generate_all(group, depth=0, dest_file=None):
    if not dest_file:
        dest = TOPSAIL_DIR / "docs" / "toolbox.generated" / "index.rst"
        dest_file = open(dest, "w")

    try:
        if depth == 0:
            print(f"""
Toolbox Documentation
=====================
            """, file=dest_file)

        for key in dir(group):
            if key.startswith("_"): continue
            component = getattr(group, key)
            doc = fire.docstrings.parse(component.__doc__)
            if depth == 0:
                print(f"""
``{component.__name__.lower()}``
{'*'*(len(component.__name__)+4)}

::

    {doc.summary or '(no summary)'}
    {doc.description or ""}

                """, file=dest_file)
            else:
                func_name = component.__func__.__qualname__ if hasattr(component, "ansible_role") \
                    else component.__qualname__
                print(f"* :doc:`{component.__name__} <{func_name}>`\t {doc.summary}", file=dest_file)

            if isinstance(component, type):
                next_group = component()
                generate_all(next_group, depth+1, dest_file)
                continue

            _generate_config(component)

    finally:
        if depth == 0:
            dest_file.close()
