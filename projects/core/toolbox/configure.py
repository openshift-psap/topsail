import os
import sys
import logging

import pathlib

from topsail.testing import env, config, run, rhods, visualize, configure_logging, prepare_user_pods, export
configure_logging()

TOPSAIL_DIR = pathlib.Path(__file__).absolute().parent.parent.parent.parent

class Configure:
    """
    Commands relating to TOPSAIL testing configuration
    """

    def init(self, project, show_export=False, shell=True, preset=None, presets=[]):
        """
        Initializes a custom configuration file for a TOPSAIL project

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

        if "CI_ARTIFACTS_CONFIG_INITED" in os.environ:
            logging.error("Already initialize ...")
            sys.exit(1)
        else:
            os.environ["CI_ARTIFACTS_CONFIG_INITED"] = "true"

        env.init()
        config.init(base_dir)

        if preset or presets:
            self.apply(preset, presets)

        if show_export or shell:
            print(f"""
export ARTIFACT_DIR={os.environ['ARTIFACT_DIR']}
export CI_ARTIFACTS_FROM_CONFIG_FILE={os.environ['CI_ARTIFACTS_FROM_CONFIG_FILE']}
export CI_ARTIFACTS_FROM_COMMAND_ARGS_FILE={os.environ['CI_ARTIFACTS_FROM_COMMAND_ARGS_FILE']}
export CI_ARTIFACTS_CONFIG_INITED={os.environ['CI_ARTIFACTS_CONFIG_INITED']}
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

        if "CI_ARTIFACTS_CONFIG_INITED" not in os.environ:
            logging.error("Configuration not initialized ...")
            sys.exit(1)

        env.init()
        config.init(env.ARTIFACT_DIR)

        if not (preset or presets):
            logging.error("Need to pass --preset or --presets parameters")
            sys.exit(1)

        name = config.ci_artifacts.get_config("ci_presets.name") or "Manual config"
        config.ci_artifacts.set_config("ci_presets.names", [])

        found = False
        if preset:
            found = True
            config.ci_artifacts.apply_preset(preset, do_dump=False)
            name = f"{name} | {preset}"

        if presets:
            found = True
            for _preset in presets:
                config.ci_artifacts.apply_preset(_preset, do_dump=False)
                name = f"{name} | {_preset}"

        config.ci_artifacts.set_config("ci_presets.name", name)
        print()
        logging.info(f"Configuration name: {name}")

    def get(self, key):
        """
        Gives the value of a given key, in the current configuration file

        Args:
          key: the key to lookup in the configuration file
        """

        if "CI_ARTIFACTS_CONFIG_INITED" not in os.environ:
            logging.error("Configuration not initialized ...")
            sys.exit(1)

        env.init()
        config.init(env.ARTIFACT_DIR)
        print("---")
        print(config.ci_artifacts.get_config(key, print=False))

    def name(self):
        """
        Gives the name of the current configuration
        """

        if "CI_ARTIFACTS_CONFIG_INITED" not in os.environ:
            logging.error("Configuration not initialized ...")
            sys.exit(1)

        env.init()
        config.init(env.ARTIFACT_DIR)
        print("---")
        print(config.ci_artifacts.get_config("ci_presets.name", print=False))
