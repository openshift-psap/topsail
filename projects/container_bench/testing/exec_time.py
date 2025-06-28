import subprocess
import time
import argparse
import sys

DEFAULT_OUTPUT_FILE = "command_output.txt"
DEFAULT_TIME_LOG_FILE = "execution_time.log"


def execute_command(command_list):
    """
    Executes a command and captures its output, error, and execution time.

    Args:
        command_list (list): A list of strings representing the command and its arguments.

    Returns:
        tuple: (stdout, stderr, return_code, execution_time)
               stdout (str): Standard output of the command.
               stderr (str): Standard error of the command.
               return_code (int): Return code of the command.
               execution_time (float): Time taken to execute the command in seconds.
    """
    start_time = time.perf_counter()
    process = subprocess.Popen(
        command_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    process.wait()
    end_time = time.perf_counter()
    execution_time = end_time - start_time

    return_code = process.returncode
    stdout = "".join(process.stdout)
    stderr = "".join(process.stderr)

    return stdout, stderr, return_code, execution_time


def write_to_file(filepath, content):
    with open(filepath, 'a') as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(
        description="Execute a command, log its execution time, and save its output.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="The command to execute and its arguments (e.g., ls -l /tmp or ping google.com -c 4)."
    )
    parser.add_argument(
        "--output-file",
        default=DEFAULT_OUTPUT_FILE,
        help=f"File to store the command's stdout and stderr (default: {DEFAULT_OUTPUT_FILE})"
    )
    parser.add_argument(
        "--time-log-file",
        default=DEFAULT_TIME_LOG_FILE,
        help=f"File to log the command's execution time (default: {DEFAULT_TIME_LOG_FILE})"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\nError: No command provided.", file=sys.stderr)
        sys.exit(1)

    command_to_run = args.command
    output_file = args.output_file
    time_log_file = args.time_log_file

    stdout, stderr, return_code, exec_time = execute_command(command_to_run)

    output_content = f"--- Command: {' '.join(command_to_run)} ---\n"
    output_content += f"Return Code: {return_code}\n\n"
    if stdout:
        output_content += "--- STDOUT ---\n"
        output_content += stdout
        output_content += "\n"
    if stderr:
        output_content += "--- STDERR ---\n"
        output_content += stderr
        output_content += "\n"
    output_content += "--- END ---\n\n"

    write_to_file(output_file, output_content)

    time_log_content = f"Command: \"{' '.join(command_to_run)}\"\n"
    time_log_content += f"ExecutionTime: {exec_time:.4f}s\n"
    time_log_content += f"ReturnCode: {return_code}\n"

    write_to_file(time_log_file, time_log_content)

    if return_code != 0:
        print(f"\nWarning: Command exited with return code {return_code}", file=sys.stderr)


if __name__ == "__main__":
    main()
