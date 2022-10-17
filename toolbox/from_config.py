import sys, os
import yaml
import io

import jinja2
import jinja2.filters

from toolbox._common import RunAnsibleRole

class FromConfig:
    """
    Run `ci-artifacts` toolbox commands from a single config file
    """
    @staticmethod
    def run(group, command,
            config_file=None,
            command_args_file=None,
            prefix="", suffix="",
            extra: dict = {},
            show_args=False,
            ):
        """
        Run `ci-artifacts` toolbox commands from a single config file.

        Args:
          group: Group from which the command belongs.
          command: Command to call, within the group.
          config_file: Configuration file from which the parameters will be looked up. Can be passed via the CI_ARTIFACTS_FROM_CONFIG_FILE environment variable.
          command_args_file: Command argument configuration file. Can be passed via the CI_ARTIFACTS_FROM_COMMAND_ARGS_FILE environment variable.
          prefix: Prefix to apply to the role name to lookup the command options.
          suffix: Suffix to apply to the role name to lookup the command options.
          extra: Extra arguments to pass to the commands. Use the dictionnary notation: '{arg1: val1, arg2: val2}'.
          show_args: Print the generated arguments on stdout and exit, or only a given argument if a value is passed.
        """

        if not config_file:
            config_file = os.getenv("CI_ARTIFACTS_FROM_CONFIG_FILE", None)
        if not config_file:
            raise ValueError("--config_file argument must have a value.")

        if not command_args_file:
            command_args_file = os.getenv("CI_ARTIFACTS_FROM_COMMAND_ARGS_FILE", None)
        if not command_args_file:
            raise ValueError("--command_args_file argument must have a value.")


        import run_toolbox
        toolbox = run_toolbox.Toolbox()

        group_obj = getattr(toolbox, group)
        command_obj = getattr(group_obj, command.replace("-", "_"))

        with open(config_file) as f:
            config = yaml.safe_load(f)

        with open(command_args_file) as f:
            # parse the file as yaml and dump it a string,
            # to resolve yaml aliases
            command_args = f.read()

        @jinja2.filters.pass_environment
        def or_env(environment, value, attribute=None):
            if value:
                return value

            if not attribute:
                raise ValueError("An attribute must be passed to env_override ...")

            return os.getenv(attribute)

        jinja2.filters.FILTERS["or_env"] = or_env

        command_args_tpl = jinja2.Template(command_args)
        command_args_rendered = command_args_tpl.render(config)

        command_args = yaml.safe_load(command_args_rendered)

        config_key = f"{group} {command}"
        if prefix:
            config_key = f"{prefix}/{config_key}"
        if suffix:
            config_key = f"{config_key}/{suffix}"

        try:
            command_args = command_args[config_key].copy()
        except KeyError:
            print(f"ERROR: key '{config_key}' not found. Available keys: \n-",
                  "\n- ".join(sorted(config.keys())))
            raise SystemExit(1)

        if not isinstance(extra, dict):
            print(f"ERROR: --extra must be a dictionnary. Got '{extra}', type '{extra.__class__.__name__}'.")
            raise SystemExit(1)

        command_args.update(extra)

        if show_args:
            if show_args is True:
                print(yaml.dump(command_args))
            else:
                print(command_args[show_args])

            raise SystemExit(0) # exit here in show-args mode

        for key in list(command_args):
            if key.startswith("_"):
                del command_args[key]

        run_ansible_role = command_obj(None, **command_args)

        run_ansible_role.py_command_name = config_key
        run_ansible_role.py_command_args = command_args

        return run_ansible_role
