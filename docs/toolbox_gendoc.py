#!/usr/bin/env python
import sys
import io
import re

# Import the toolbox run script
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import run_toolbox

def members(obj):
    return [member for member in dir(obj) if not member.startswith("__")]

def ansi_remove(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


toolbox = run_toolbox.Toolbox()

for command in members(toolbox):
    print(f"{command}")
    print('"' * len(command))
    for subcommand in members(getattr(toolbox, command)):
        stderr_capture = io.StringIO()
        _stderr = sys.stderr
        sys.stderr = stderr_capture
        command_args = ["./run_toolbox.py", command, subcommand]
        sys.argv = command_args + ["--help"]
        run_toolbox.main(no_exit=True)
        sys.stderr =_stderr

        cmdexample = " ".join(command_args)
        print(f"``{cmdexample}``")
        print()
        print(f".. code-block:: text")
        print()
        print("\n".join(f"    {ansi_remove(line)}" for line in stderr_capture.getvalue().splitlines()[2:]))
        print()
        print()
