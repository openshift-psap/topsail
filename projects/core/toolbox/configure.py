import os
import sys
import logging

import pathlib

from projects.core.library import env, config, run, configure_logging
configure_logging()

TOPSAIL_DIR = pathlib.Path(config.__file__).parents[3]

class Configure:
    """
    Commands relating to TOPSAIL testing configuration
    """

    def enter(self, project, show_export=False, shell=True, preset=None, presets=[]):
        """
        Enter into a custom configuration file for a TOPSAIL project

        Args:
          project: the name of the projec to configure
          show_export: show the export command
          shell: if False, do nothing. If True, exec the default shell. Any other value is executed.
          preset: a preset to apply
          presets: a list of presets to apply
        """

        base_dir = TOPSAIL_DIR / "projects" / project / "testing"
        if not base_dir.is_dir():
            raise ValueError(f"Invalid project directory: {base_dir}")

        if "ARTIFACT_DIR" not in os.environ:
            os.environ["ARTIFACT_DIR"] = str(pathlib.Path("/tmp") / project)

        if "TOPSAIL_CONFIG_INITED" in os.environ:
            logging.error("Already initialize ...")
            sys.exit(1)
        else:
            os.environ["TOPSAIL_CONFIG_INITED"] = "true"

        env.init()

        if (config_file := env.ARTIFACT_DIR / "config.yaml").exists():
            logging.warning(f"{config_file} already exists. Deleting it.")
            config_file.unlink()

        config.init(base_dir)

        if preset or presets:
            self.apply(preset, presets)

        if show_export or shell:
            print(f"""
export ARTIFACT_DIR={os.environ['ARTIFACT_DIR']}
export TOPSAIL_FROM_CONFIG_FILE={os.environ['TOPSAIL_FROM_CONFIG_FILE']}
export TOPSAIL_FROM_COMMAND_ARGS_FILE={os.environ['TOPSAIL_FROM_COMMAND_ARGS_FILE']}
export TOPSAIL_CONFIG_INITED={os.environ['TOPSAIL_CONFIG_INITED']}
        """)

        if shell:
            if shell is True:
                shell = os.environ["SHELL"]

            if preset:
                logging.info(f"Preset '{preset}' applied.")
            if presets:
                logging.info(f"Presets '{presets}' applied.")

            logging.warning(f"Entering the configured environment ... ({shell})")
            os.system(shell)
            logging.info("Exiting the configured environment ...")

    def apply(self, preset=None, presets=[]):
        """
        Applies a preset (or a list of presets) to the current configuration file

        Args:
          preset: a preset to apply
          presets: a list of presets to apply
        """

        if "TOPSAIL_CONFIG_INITED" not in os.environ:
            logging.error("Configuration not initialized ...")
            sys.exit(1)

        env.init()
        config.init(env.ARTIFACT_DIR)

        if not (preset or presets):
            logging.error("Need to pass --preset or --presets parameters")
            sys.exit(1)

        name = config.project.get_config("ci_presets.name") or "Manual config"
        config.project.set_config("ci_presets.names", [])

        found = False
        if preset:
            found = True
            config.project.apply_preset(preset, do_dump=False)
            name = f"{name} | {preset}"

        if presets:
            found = True
            for _preset in presets:
                config.project.apply_preset(_preset, do_dump=False)
                name = f"{name} | {_preset}"

        config.project.set_config("ci_presets.name", name)
        print()
        logging.info(f"Configuration name: {name}")

    def get(self, key):
        """
        Gives the value of a given key, in the current configuration file

        Args:
          key: the key to lookup in the configuration file
        """

        if "TOPSAIL_CONFIG_INITED" not in os.environ:
            logging.error("Configuration not initialized ...")
            sys.exit(1)

        env.init()
        config.init(env.ARTIFACT_DIR)
        print("---")
        print(config.project.get_config(key, print=False))

    def name(self):
        """
        Gives the name of the current configuration
        """

        if "TOPSAIL_CONFIG_INITED" not in os.environ:
            logging.error("Configuration not initialized ...")
            sys.exit(1)

        env.init()
        config.init(env.ARTIFACT_DIR)
        print("---")
        print(config.project.get_config("ci_presets.name", print=False))
