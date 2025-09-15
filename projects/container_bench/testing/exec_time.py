import subprocess
import time
import argparse
import sys
import psutil
import threading
import json
import platform
import re
import logging

DEFAULT_OUTPUT_FILE = "output.txt"
DEFAULT_TIME_LOG_FILE = "time.log"
DEFAULT_METRICS_LOG_FILE = "metrics.log"
DEFAULT_INTERVAL = 0.1


class PowerMetrics:
    """
    Manages powermetrics process for continuous power monitoring on macOS.

    This class starts a long-running powermetrics subprocess that outputs
    power consumption data continuously. The process runs in parallel with
    the measured command and provides real-time power measurements through
    its stdout stream.
    """
    def __init__(self, interval=DEFAULT_INTERVAL):
        self.interval = int(interval * 1000.0)
        self.process = None
        self.is_running = False

    def start_monitoring(self):
        """Start the powermetrics process for continuous monitoring.

        Starts a long-running powermetrics subprocess that continuously outputs
        power measurements. This process runs in parallel with the measured command
        and provides real-time power consumption data through its stdout.

        Returns:
            bool: True if powermetrics started successfully, False otherwise.
        """
        if platform.system() != "Darwin":
            logging.info("Power monitoring not available on non-Darwin systems")
            return False

        return self._darwin_start()

    def _darwin_start(self):
        try:
            # To enable powermetrics to run without a password prompt, add this line to sudoers:
            # Run 'sudo visudo' and add:
            # <username> ALL = (root) NOPASSWD: /usr/bin/powermetrics
            # Replace <username> with your actual username (e.g., john ALL = (root) NOPASSWD: /usr/bin/powermetrics)
            # This allows the script to run powermetrics with sudo without interactive password input
            cmd = [
                "sudo",
                "-n",
                "powermetrics",
                "--samplers",
                "cpu_power",
                "-i", str(self.interval),
                "-n", "-1",
                "-b", "1"
            ]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self.is_running = True
            # Verify the process didn't exit immediately (e.g., permission error)
            time.sleep(0.2)
            if self.process.poll() is not None:
                err = ""
                try:
                    err = self.process.stderr.read().strip()
                except Exception:
                    pass
                logging.error(f"powermetrics exited immediately (code {self.process.returncode}). {err}")
                logging.error("Check sudoers configuration to allow powermetrics without a password.")
                self.is_running = False
                self.process = None
                return False
            return True

        except FileNotFoundError as e:
            logging.error(f"powermetrics not found: {e}")
            return False
        except Exception as e:
            logging.error(f"Failed to start powermetrics: {e}")
            return False

    def stop_monitoring(self):
        """Stop the powermetrics process.

        Gracefully terminates the powermetrics subprocess by sending SIGTERM.
        If the process doesn't terminate within 5 seconds, it will be forcefully
        killed with SIGKILL.
        """
        if self.process and self.is_running:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
                logging.warning("PowerMetrics process was forcefully killed")
            except Exception as e:
                logging.error(f"Error stopping powermetrics: {e}")
            finally:
                self.is_running = False
                self.process = None

    def get_stdout(self):
        """Get the stdout stream of the powermetrics process.

        Returns:
            TextIOWrapper or None: The stdout stream if process is running, None otherwise.
        """
        return self.process.stdout if self.process else None


class Measurements:
    def __init__(self, interval=DEFAULT_INTERVAL):
        self.cpu_usage = []
        self.network_usage = {"send": [], "recv": []}
        self.disk_usage = {"read": [], "write": []}
        self.memory_usage = []
        self.interval = interval
        self.execution_time = 0.0
        self.return_code = 0
        self.power_usage = []

    def to_dict(self):
        return {
            "cpu_usage": self.cpu_usage,
            "network_usage": self.network_usage,
            "disk_usage": self.disk_usage,
            "memory_usage": self.memory_usage,
            "interval": self.interval,
            "execution_time": self.execution_time,
            "return_code": self.return_code,
            "power_usage": self.power_usage,
        }

    def set_execution_time(self, exec_time):
        self.execution_time = exec_time

    def set_return_code(self, return_code):
        self.return_code = return_code


def parse_power_line(line):
    """Parse a line containing power information to extract watts.

    Extracts power values from powermetrics output lines that contain
    "Combined Power". Supports both watts (W) and milliwatts (mW) units.

    Args:
        line (str): A line from powermetrics output containing power data.

    Returns:
        float: Power consumption in watts, or 0.0 if parsing fails.
    """
    try:
        # Extract "<value> <unit>" where unit is W or mW (case-insensitive)
        match = re.search(r'(\d+\.?\d*)\s*(mW|W)', line, re.IGNORECASE)
        if match:
            value_str, unit = match.groups()
            value = float(value_str)
            unit = unit.lower()
            if unit == "mw":
                return value / 1000.0  # Convert mW to W
            return value  # assume W
    except (ValueError, IndexError, AttributeError) as e:
        logging.error(f"Error parsing power line '{line}': {e}")
    return 0.0


def read_power_metrics(read_event, measurements, stdout_stream):
    """
    Reads power usage data from a running powermetrics process in a separate thread.

    This function continuously reads power measurements from the stdout stream of a
    powermetrics process. It only collects power data when the read_event is set,
    allowing precise control over when power measurements are recorded during
    command execution.

    Args:
        read_event (threading.Event): Controls when to collect power measurements.
        measurements (Measurements): Container used to store the collected data.
        stdout_stream: The stdout stream from the powermetrics process.

    """
    if not stdout_stream:
        return

    try:
        for line in stdout_stream:
            line = line.strip()
            if "Combined Power" in line and read_event.is_set():
                measurements.power_usage.append(parse_power_line(line))
    except Exception as e:
        logging.error(f"Error in power monitoring: {e}")


def monitor_resources(stop_event, measurements):
    """
    Monitors system-wide CPU, network, disk, and memory usage in a separate thread.

    Args:
        stop_event (threading.Event): Signals when to stop monitoring.
        measurements (Measurements): Container used to store the collected data.
    """
    net_send_list = []
    net_recv_list = []
    disk_write_list = []
    disk_read_list = []

    # Get initial network and disk counters
    last_net_io = psutil.net_io_counters()
    last_disk_io = psutil.disk_io_counters()

    while not stop_event.is_set():
        # Overall System CPU Usage
        measurements.cpu_usage.append(psutil.cpu_percent(interval=measurements.interval))

        # --- Network Usage ---
        current_net_io = psutil.net_io_counters()
        bytes_sent = current_net_io.bytes_sent - last_net_io.bytes_sent
        bytes_recv = current_net_io.bytes_recv - last_net_io.bytes_recv
        net_send_list.append(bytes_sent)
        net_recv_list.append(bytes_recv)
        last_net_io = current_net_io

        # --- Disk I/O ---
        current_disk_io = psutil.disk_io_counters()
        read_bytes = current_disk_io.read_bytes - last_disk_io.read_bytes
        write_bytes = current_disk_io.write_bytes - last_disk_io.write_bytes
        disk_read_list.append(read_bytes)
        disk_write_list.append(write_bytes)
        last_disk_io = current_disk_io

        # --- Memory Usage ---
        measurements.memory_usage.append(psutil.virtual_memory().percent)

    # Extend the lists with the collected data
    measurements.network_usage["send"] = net_send_list
    measurements.network_usage["recv"] = net_recv_list
    measurements.disk_usage["read"] = disk_read_list
    measurements.disk_usage["write"] = disk_write_list


def execute_command(command_list, stop_event, read_power_event, monitor_thread):
    """
    Executes a command and captures its output, error, and execution time.

    Starts the monitoring thread for system resources, sets the power reading event
    to begin power data collection, then executes the command and waits for completion.
    The power monitoring reads from a pre-started powermetrics process.

    Args:
        command_list (list): A list of strings representing the command and its arguments.
        stop_event (threading.Event): Signals the monitor thread to stop.
        read_power_event (threading.Event): Controls when power data is collected.
        monitor_thread (threading.Thread): Thread sampling CPU/net/disk/memory.

    Returns:
        tuple: (stdout, stderr, return_code, execution_time)
               stdout (str): Standard output of the command.
               stderr (str): Standard error of the command.
               return_code (int): Return code of the command.
               execution_time (float): Time taken to execute the command in seconds.
    """
    monitor_thread.start()
    read_power_event.set()
    start_time = time.perf_counter()
    try:
        with subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        ) as process:
            stdout, stderr = process.communicate()
            process.wait()
            return_code = process.returncode
        end_time = time.perf_counter()
    except Exception as e:
        stdout, stderr, return_code, end_time = "", str(e), -1, time.perf_counter()
    finally:
        stop_event.set()
        read_power_event.clear()
        monitor_thread.join()

    execution_time = end_time - start_time

    return stdout, stderr, return_code, execution_time


def write_to_file(filepath, content):
    with open(filepath, 'a') as f:
        f.write(content)


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )

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
    parser.add_argument(
        "--metrics-log-file",
        default=DEFAULT_METRICS_LOG_FILE,
        help=f"File to log the metrics during run of command (default: {DEFAULT_METRICS_LOG_FILE})"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        logging.error("\nError: No command provided.")
        sys.exit(1)

    measurements = Measurements(interval=DEFAULT_INTERVAL)
    stop_event = threading.Event()
    read_power_event = threading.Event()

    command_to_run = args.command

    # Start powermetrics process and power reading thread
    # The powermetrics process runs continuously, but power data is only
    # collected when read_power_event is set during command execution
    power_metrics = PowerMetrics(interval=measurements.interval)
    if not power_metrics.start_monitoring():
        logging.warning("Power monitoring unavailable; proceeding without power data.")

    power_usage_thread = threading.Thread(
        target=read_power_metrics,
        args=(read_power_event, measurements, power_metrics.get_stdout()),
        daemon=True
    )
    power_usage_thread.start()

    monitor_thread = threading.Thread(
        target=monitor_resources,
        args=(stop_event, measurements),
        daemon=True
    )

    stdout, stderr, return_code, exec_time = execute_command(
        command_to_run,
        stop_event,
        read_power_event,
        monitor_thread
    )
    measurements.set_execution_time(exec_time)
    measurements.set_return_code(return_code)

    power_metrics.stop_monitoring()
    power_usage_thread.join()

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

    write_to_file(args.output_file, output_content)

    time_log_content = f"Command: \"{' '.join(command_to_run)}\"\n"
    time_log_content += f"ExecutionTime: {exec_time:.4f}s\n"
    time_log_content += f"ReturnCode: {return_code}\n"

    write_to_file(args.time_log_file, time_log_content)
    write_to_file(args.metrics_log_file, json.dumps(measurements.to_dict(), separators=(',', ':')) + "\n")

    if return_code != 0:
        logging.warning(f"Command exited with return code {return_code}")
        logging.warning(f"STDERR: {stderr}")


if __name__ == "__main__":
    main()
