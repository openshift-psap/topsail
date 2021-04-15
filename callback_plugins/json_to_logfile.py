# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# imported from /usr/lib/python3.8/site-packages/ansible/plugins/callback/syslog_json.py
# extending class from /usr/lib/python3.8/site-packages/ansible/plugins/callback/__init__.py

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json

import logging
import logging.handlers

import socket

from ansible.plugins.callback import CallbackBase

DOCUMENTATION = '''
    callback: json_to_logfile
    callback_type: notification
    requirements:
      - whitelist in configuration
    short_description: sends JSON events to a file
    version_added: "1.9"
    description:
      - This plugin logs ansible-playbook and ansible runs to a file in then JSON format.
    options:
      logfile:
        description: filename where the logs will be stored
        env:
        - name: ANSIBLE_JSON_TO_LOGFILE
        default: /tmp/ansible.log.json
        ini:
        - section: callback_json_to_file
          key: logfile
'''



class CallbackModule(CallbackBase):
    """
    logs ansible playbook execution to a file in the JSON format
    """

    CALLBACK_VERSION = 1.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'json_to_file'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        super(CallbackModule, self).__init__()

    def set_options(self, task_keys=None, var_options=None, direct=None):

        super(CallbackModule, self).set_options(task_keys=task_keys, var_options=var_options, direct=direct)

        self.logfile = self.get_option("logfile")

        with open(self.logfile, "a+") as f:
            print("[", file=f)
        self.is_open = True

        print("JSON_TO_LOGFILE: Storing json logs in", self.logfile)
        self.hostname = socket.gethostname()

    def _write(self, data, finished=False):
        self._warn_if_not_open()

        if not finished:
            end = "," + "\n"
        else:
            end = "\n]" + "\n"
            self.is_open = False

        with open(self.logfile, "a+") as f:
            print(json.dumps(data, indent=4, sort_keys=True), end=end, file=f)

    def _warn_if_not_open(self):
        if self.is_open: return

        print("JSON_TO_LOGFILE: WARNING: logfile already closed ....")

    def playbook_on_stats(self, stats):
        hosts = set()
        for dictt in stats.ok, stats.failures, stats.skipped, stats.rescued:
            hosts.update(dictt.keys())

        all_stats = {}
        for host in hosts:
            all_stats[host] = stats.summarize(host)

        self._write({"scope": "playbook",
                     "log_level": "info",
                     "status": "finished",
                     "stats": all_stats,
                     },
                    finished=True)

    def runner_on_failed(self, host, res, ignore_errors=False):
        self._write({"scope": "task",
                     "status": "FAILED",
                     "log_level": "error",
                     "host": host,
                     "hostname": self.hostname,
                     "ignore_errors": ignore_errors,
                     "message": res})

    def runner_on_ok(self, host, res):
        self._write({"scope": "task",
                     "status": "OK",
                     "log_level": "info",
                     "host": host,
                     "hostname": self.hostname,
                     "message": res})

    def runner_on_skipped(self, host, item=None):
        self._write({"scope": "task",
                     "status": "SKIPPED",
                     "log_level": "info",
                     "host": host,
                     "hostname": self.hostname,
                     "item": item,
                     "message": "skipped"})

    def runner_on_unreachable(self, host, res):
        self._write({"scope": "task",
                     "status": "UNREACHABLE",
                     "log_level": "error",
                     "host": host,
                     "hostname": self.hostname,
                     "message": res})

    def runner_on_async_failed(self, host, res, jid):
        self._write({"scope": "task",
                     "status": "FAILED",
                     "log_level": "error",
                     "host": host,
                     "jid": jid,
                     "hostname": self.hostname,
                     "message": res})

    def playbook_on_import_for_host(self, host, imported_file):
        self._write({"scope": "playbook",
                     "status": "IMPORTED",
                     "log_level": "error",
                     "host": host,
                     "hostname": self.hostname,
                     "file": imported_file})

    def playbook_on_not_import_for_host(self, host, missing_file):
        self._write({"scope": "playbook",
                     "status": "NOT IMPORTED",
                     "log_level": "error",
                     "host": host,
                     "hostname": self.hostname,
                     "file": missing_file})
