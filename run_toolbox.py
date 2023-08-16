#!/usr/bin/env python

import sys

try:
    import fire
except ModuleNotFoundError:
    print("The toolbox requires the Python `fire` package, see requirements.txt for a full list of requirements")
    sys.exit(1)

import toolbox

def main(no_exit=False):
    # Print help rather than opening a pager
    fire.core.Display = lambda lines, out: print(*lines, file=out)

    # Launch CLI, get a runnable
    runnable = None
    try:
        runnable = fire.Fire(toolbox.Toolbox())
    except fire.core.FireExit:
        if not no_exit:
            raise

    # Run the actual workload
    try:
        if hasattr(runnable, "_run"):
            runnable._run()
        else:
            # CLI didn't resolve completely - either by lack of arguments
            # or use of `--help`. This is okay.
            pass
    except SystemExit as e:
        if not no_exit:
            sys.exit(e.code)


if __name__ == "__main__":
    main()
