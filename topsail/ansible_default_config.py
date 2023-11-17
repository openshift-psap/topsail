import yaml
import pathlib
import sys
import logging

import fire.inspectutils
import fire.docstrings


def _generate_config(component):
    if not hasattr(component, "ansible_role"):
        print(f"{component.__qualname__}\n- not an ansible role.\n")
        return

    if getattr(component, "ansible_skip_config_generation", False):
        print(f"{component.__qualname__}\n- skipping the config file generation (@AnsibleSkipConfigGeneration).\n")
        return

    ansible_mapped_params = getattr(component, "ansible_mapped_params", False)
    ansible_constants = getattr(component, "ansible_constants", [])

    if not (ansible_constants or ansible_mapped_params):
        print(f"{component.__qualname__}\n- skipping the config file generation (no @AnsibleMappedParams nor @AnsibleConstant).\n")
        return

    doc = fire.docstrings.parse(component.__doc__)
    spec = fire.inspectutils.GetFullArgSpec(component)
    args_with_no_defaults = spec.args[:len(spec.args) - len(spec.defaults)]
    args_with_defaults = spec.args[len(spec.args) - len(spec.defaults):]
    args_defaults = dict(zip(args_with_defaults, spec.defaults))

    args = {}
    for arg in doc.args or {}:
        args[arg.name] = arg

    classname = component.__qualname__.partition(".")[0].lower()

    dest = pathlib.Path("roles") / classname / component.ansible_role / "defaults" / "main" / "config.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"{component.__qualname__}\n- generating {dest} ...\n")

    with open(dest, "w") as f:
        print("# Auto-generated file, do not edit manually ...", file=f)
        print(f"# Toolbox generate command: {' '.join(sys.argv[1:])}", file=f)
        print(f"# Source component: {component.__qualname__}", file=f)

        mapped_params = args_with_no_defaults + args_with_defaults \
            if ansible_mapped_params else []

        if len(mapped_params) > 0:
            print("", file=f)
            print("# Parameters", file=f)

        for i, arg in enumerate(mapped_params):
            try:
                description = args[arg].description
            except KeyError:
                description = f"Missing documentation for {arg}"

            print(f"# {description}", file=f)

            if arg in args_with_no_defaults:
                default_value = ""
                print("# Mandatory value", file=f)
            else:
                default_value = args_defaults.get(arg, '')

            try:
                print(f"# Type: {spec.annotations[arg].__name__.title()}", file=f)
            except KeyError: pass # no type annotation, ignore

            ansible_arg_name = f"{component.ansible_role}_{arg}"
            print(yaml.dump({ansible_arg_name: default_value}).strip() if default_value != "" \
                  else f"{ansible_arg_name}:", file=f)
            if i < len(mapped_params)-1:
                print("", file=f)
        
        if len(ansible_constants) > 0:
            print("", file=f)
            print("# Constants", file=f)

        for i, constant in enumerate(ansible_constants):
            if not constant["description"]:
                logging.error(f"Shouldn't generate a config file with an empty constant description :/ Is @AnsibleSkipConfigGeneration missing on {component.__qualname__}?")

            print(f"# {constant['description']}", file=f)
            print(f"# Defined as a constant in {component.__qualname__}", file=f)
            print(yaml.dump({f"{component.ansible_role}_{constant['name']}": constant["value"]}).strip(), file=f)
            if i < len(ansible_constants)-1:
                print("", file=f)

def generate_all(group):
    for key in dir(group):
        if key.startswith("_"): continue
        component = getattr(group, key)

        if isinstance(component, type):
            next_group = component()
            generate_all(next_group)
            continue

        _generate_config(component)
