import sys, os
import pathlib
import importlib
import itertools
import logging
import pkg_resources

class Toolbox:
    """
    The Topsail Toolbox
    """

    def __init__(self):

        top_dir = pathlib.Path(__file__).resolve().parent
        topsail_package_location = ''
        try:
            topsail_package_location = pkg_resources.resource_filename('topsail', '')
            logging.info(f"Topsail package location: {topsail_package_location}")
        except pkg_resources.ResolutionError:
            logging.info("Topsail is not installed as a package")

        import_prefix=''
        if "dist-packages" in str(top_dir):
            logging.info("Running from the package binary")
            import_prefix='topsail.'
        else:
            logging.info("Running from the run_toolbox.py script")

        for toolbox_file in itertools.chain((top_dir / "projects").glob("*/toolbox/*.py"), (top_dir / "topsail").glob("*.py")):

            project_toolbox_module = import_prefix + str(toolbox_file.relative_to(top_dir).with_suffix("")).replace(os.path.sep, ".")
            try:
                mod = importlib.import_module(project_toolbox_module)
            except ModuleNotFoundError as e:
                logging.fatal(str(e))
                sys.exit(1)

            toolbox_name = toolbox_file.with_suffix("").name

            if toolbox_name.startswith("_"): continue

            if hasattr(mod, "__entrypoint"):
                self.__dict__[toolbox_name] = getattr(mod, "__entrypoint")
                continue

            try:
                self.__dict__[toolbox_name] = getattr(mod, toolbox_name.title())
            except AttributeError as e:
                logging.fatal(str(e)) # AttributeError: module 'projects.notebooks.toolbox.notebooks' has no attribute 'Notebooks'
                sys.exit(1)
