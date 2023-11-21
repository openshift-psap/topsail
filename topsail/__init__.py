import sys, os
import pathlib
import importlib
import itertools
import logging

class Toolbox:
    """
    The Topsail Toolbox
    """

    def __init__(self):

        top_dir = pathlib.Path(__file__).resolve().parent.parent


        for toolbox_file in itertools.chain((top_dir / "projects").glob("*/toolbox/*.py"), (top_dir / "topsail").glob("*.py")):

            project_toolbox_module = str(toolbox_file.relative_to(top_dir).with_suffix("")).replace(os.path.sep, ".")
            mod = importlib.import_module(project_toolbox_module)
            toolbox_name = toolbox_file.with_suffix("").name

            if toolbox_name.startswith("_"): continue

            if hasattr(mod, "__entrypoint"):
                self.__dict__[toolbox_name] = getattr(mod, "__entrypoint")
                continue

            try:
                self.__dict__[toolbox_name] = getattr(mod, toolbox_name.title())
            except AttributeError as e:
                logging.warning(str(e)) # AttributeError: module 'projects.notebooks.toolbox.notebooks' has no attribute 'Notebooks'
