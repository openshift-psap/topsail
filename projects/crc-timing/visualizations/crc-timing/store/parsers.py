import types
import pathlib
import logging
import yaml
import os
import json
import datetime
import urllib
import uuid
import re

import jsonpath_ng

import matrix_benchmarking.cli_args as cli_args
import matrix_benchmarking.store.prom_db as store_prom_db

import projects.matrix_benchmarking.visualizations.helpers.store as helpers_store
import projects.matrix_benchmarking.visualizations.helpers.store.parsers as helpers_store_parsers

from . import prom as workload_prom

register_important_file = None # will be when importing store/__init__.py

SYSTEMD_DATE_TIME_FMT = "%a %Y-%m-%d %H:%M:%S %Z"
SYSTEMD_UNIT_TIME_FMT = "%Y %b %d %H:%M:%S" # needs the year 2025 to be prepended

artifact_dirnames = types.SimpleNamespace()
artifact_paths = types.SimpleNamespace() # will be dynamically populated
artifact_dirnames.JOURNALCTL_U_FILES = "journalctl_u_*.txt"

IMPORTANT_FILES = [
    "systemd-analyze_dump.txt",
    "oc-get-clusteroperators.yaml",
    "systemd-analyze_critical-chain_crc-custom.txt",
    "systemd-analyze_critical-chain.txt",
    "journalctl_u_*.txt",
]


def parse_always(results, dirname, import_settings):
    # parsed even when reloading from the cache file
    results.from_local_env = helpers_store_parsers.parse_local_env(dirname)
    pass


def parse_once(results, dirname):
    # results.test_config = helpers_store_parsers.parse_test_config(dirname)
    # results.test_uuid = helpers_store_parsers.parse_test_uuid(dirname)

    results.systemd_units = _parse_systemd_units(dirname)
    results.systemd_crc_cluster_status = _parse_systemd_crc_cluster_status(dirname)
    results.systemd_crc_critical_chain = _parse_systemd_critical_chain(dirname, "systemd-analyze_critical-chain_crc-custom.txt")
    results.systemd_critical_chain = _parse_systemd_critical_chain(dirname, "systemd-analyze_critical-chain.txt")

    results.systemd_journal_duration = _parse_systemd_journal_duration(dirname)

    results.ocp_co = _parse_ocp_co(dirname)


    results.lts = None


@helpers_store_parsers.ignore_file_not_found
def _parse_systemd_critical_chain(dirname, fname):
    critical_chain = types.SimpleNamespace()

    with open(register_important_file(dirname, fname)) as f:
        critical_chain.text = f.read()

    return critical_chain


@helpers_store_parsers.ignore_file_not_found
def _parse_systemd_journal_duration(dirname):
    systemd_journal_duration = {}

    for journal_file in dirname.glob(artifact_dirnames.JOURNALCTL_U_FILES):
        entry = types.SimpleNamespace()

        lines = [
            ln for ln in register_important_file(dirname, journal_file)
            .read_text()
            .splitlines()
            if ln and not ln.startswith("-- ") # remove the journal lines starting with -- [Boot ...|Journal begins ...|...]
        ]
        if not lines:
            continue

        first_line = lines[0]
        last_line = lines[-1]
        if first_line == last_line:
            continue

        entry.start_time = datetime.datetime.strptime(f"{datetime.datetime.now().year} {first_line[:15]}", SYSTEMD_UNIT_TIME_FMT)
        entry.finish_time = datetime.datetime.strptime(f"{datetime.datetime.now().year} {last_line[:15]}", SYSTEMD_UNIT_TIME_FMT)
        entry.duration = entry.finish_time - entry.start_time
        entry.name = journal_file.name.removeprefix("journalctl_u_").removesuffix(".txt")

        systemd_journal_duration[entry.name] = entry

    return systemd_journal_duration

@helpers_store_parsers.ignore_file_not_found
def _parse_systemd_crc_cluster_status(dirname):
    systemd_crc_cluster_status = []

    with open(register_important_file(dirname, "journalctl_u_crc-cluster-status.service.txt")) as f:
        for line in f.readlines():
            if "-- Boot" in line:
                systemd_crc_cluster_status = [] # keep only the last boot
                continue

            entry = types.SimpleNamespace()

            entry.date = datetime.datetime.strptime(f"{datetime.datetime.now().year} {line[:15]}", SYSTEMD_UNIT_TIME_FMT)

            if "is still" in line:
                entry.co = line.partition(": ")[-1].split()[0].split("/")[1]
                entry.state = line.partition("is still ")[-1].partition(" after ")[0]
            elif "stabilized at" in line:
                entry.co = line.partition(": ")[-1].split()[0].split("/")[1]
                entry.state = "STABLE"
            elif ("All clusteroperators became stable" in line
                  or "All clusteroperators are still stable" in line):
                entry.co = "CLUSTER"
                entry.state = "STABLE"
            else:
                continue

            systemd_crc_cluster_status.append(entry)

    return systemd_crc_cluster_status


@helpers_store_parsers.ignore_file_not_found
def _parse_systemd_units(dirname):

    with open(register_important_file(dirname, "systemd-analyze_dump.txt")) as f:
        systemd_units = parse_systemd_dump(f.readlines())

    return systemd_units


def parse_systemd_dump(lines) -> list[dict]:
    # generated by Gemini, adapted by kpouget

    """
    Parses the multi-line string output from `systemd-analyze dump`.

    keep only the services
    """

    def keep(unit_name: str) -> bool:
        if unit_name.startswith("var-"):
            return False
        if unit_name.startswith("run-"):
            return False
        if not (unit_name.endswith(".service")
                or unit_name.endswith(".target")
                or unit_name == "system.slice"):
            return False
        return True

    units = {}
    current_unit = {}
    unit_name = None

    for line in lines:
        # A new unit section starts with a non-indented line

        if line.startswith('->'):
            # If there's a previously parsed unit, save it
            if current_unit and unit_name:
                current_unit['Unit'] = unit_name
                if keep(unit_name):
                    units[unit_name] = current_unit

            # Start a new unit
            current_unit = {}
            # The unit name might be followed by a description
            unit_name = unescape_systemd_unit(
                line.partition('-> Unit')[-1].strip().rstrip(":")
            )

            continue

        # Parse key-value pairs within a unit section
        match = re.match(r'\s+([^:]+):\s*(.*)', line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            try:
                value = datetime.datetime.strptime(value, SYSTEMD_DATE_TIME_FMT)
            except Exception:
                pass # not a date, ignore
            current_unit[key] = value

    # Append the last parsed unit after the loop finishes
    if current_unit and unit_name:
        current_unit['Unit'] = unit_name
        if keep(unit_name):
            units[unit_name] = current_unit

    return units


def unescape_systemd_unit(name: str) -> str:
    # generated by Gemini
    """
    Replicates `systemd-escape --unescape` in Python.

    It decodes \\xHH hex sequences and converts systemd's path encoding
    back into a standard file path.

    Args:
        name: The mangled systemd unit name (without the .mount suffix).

    Returns:
        The unmangled, human-readable file path.
    """

    # 1. First, remove the unit type suffix if it exists
    if name.endswith('.mount'):
        name = name[:-6]

    # 2. Define a function to replace hex codes with characters
    #    The lambda function takes a regex match object, extracts the hex
    #    part (group 1), converts it to an integer, and then to a character.
    def hex_to_char(match):
        hex_code = match.group(1)
        return chr(int(hex_code, 16))

    # 3. Replace all \xHH sequences using the helper function
    unescaped_name = re.sub(r'\\x([0-9a-fA-F]{2})', hex_to_char, name)

    return unescaped_name


@helpers_store_parsers.ignore_file_not_found
def _parse_ocp_co(dirname):

    with open(register_important_file(dirname, "oc-get-clusteroperators.yaml")) as f:
        ocp_co = yaml.safe_load(f)["items"]

    return ocp_co
