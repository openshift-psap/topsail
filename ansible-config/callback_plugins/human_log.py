import os

from ansible.plugins.callback.default import CallbackModule as default_CallbackModule
from ansible import constants as C
import ansible.executor

# extends this class: https://github.com/ansible/ansible/blob/devel/lib/ansible/plugins/callback/default.py

# mute this log message:
# "Friday 05 April 2024  15:01:14 +0200 (0:00:04.215)       0:00:04.504 **********"
import ansible_collections.ansible.posix.plugins.callback.profile_roles as profile_roles_mod
profile_roles_mod.tasktime = lambda: ""

INTERESTING_MODULE_PROPS = {
    "stat": ["path", "exists", "mode"],
    "invocation": None,
    "_ansible_no_log": None,
    "_ansible_verbose_always": None,
    "__ansible_verbose_override": None,
    "msg": None,
    "changed": None,
    "ansible_facts": None,
    "include_args": None,
    "failed_when_result": None,
    }

class CallbackModule(default_CallbackModule):
    def __display_result(self, result, color, ignore_errors=None, loop_idx=0):
        if ignore_errors not in (None, False):
            self._display.display(f"==> FAILED | ignore_errors={ignore_errors}", color=color)

        try:
            if result._result['msg'].strip():
                self._display.display(f"msg: {result._result['msg']}", color=color)
        except KeyError: pass

        try:
            if result._result.get("rc", 0) != 0:
                self._display.display(f"return code: {result._result['rc']}", color=color)
        except KeyError: pass

        if "results" in result._result:
            for idx, res in enumerate(result._result['results']):
                var = res['ansible_loop_var']
                value = res['_ansible_item_label']
                self._display.display("", color=color)
                self._display.display(f"LOOP #{idx}: {var} = {value}", color=color)
                item_result = ansible.executor.task_result.TaskResult(
                    host=result._host, task=result._task, return_data=res)
                self.__display_result(item_result, color, ignore_errors, loop_idx=idx)

            return

        def print_result_as_dict(key, d, depth=1):
            for k, v in d.items():
                if k in INTERESTING_MODULE_PROPS:
                    if INTERESTING_MODULE_PROPS[k] is None: continue
                    if v not in INTERESTING_MODULE_PROPS[k]: continue

                if not isinstance(v, dict):
                    self._display.display(f"{'  '*depth}- {k}:\t{v}", color=C.COLOR_VERBOSE)
                else:
                    self._display.display(f"{'  '*depth}- {k}", color=C.COLOR_VERBOSE)
                    print_result_as_dict(k, v, depth+1)

        try:
            self.__print_cmd(result, color)
        except KeyError:
            print_result_as_dict("_top", result._result)
            # ^^^ will print stdout and stderr
            return

        ####

        self.__print_std_lines(result, "stdout", color)
        self.__print_std_lines(result, "stderr", color)

    def __print_std_lines(self, result, std_name, color):
        if not result._result.get(f'{std_name}_lines'):
            return

        for line in result._result[f'{std_name}_lines']:
            self._display.display(f"<{std_name}> {line}", color=color)

    def __print_cmd(self, result, color):
        cmd = result._result['cmd']

        str_cmd = cmd if isinstance(cmd, str) \
            else ' '.join(cmd)

        self._display.display(f"", color=color)
        if "\n" in str_cmd:
            self._display.display(f"<command>\n{str_cmd}\n</command>", color=color)
        else:
            self._display.display(f"<command> {str_cmd}", color=color)

        self._display.display(f"", color=color)

    def v2_runner_on_skipped(self, result):
        self._print_task_banner(result._task, head=True)

        self._display.display(f"==> SKIPPED | {result._result.get('skip_reason', '(no reason provided)')}",
                              color=C.COLOR_SKIP)
        for condition in result._task.when:
            self._display.display(f"when: {condition}", C.COLOR_SKIP)


    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._print_task_banner(result._task, head=True)

        color = C.COLOR_VERBOSE if ignore_errors else C.COLOR_ERROR
        self._display.display("----- FAILED ----", C.COLOR_ERROR)
        self.__display_result(result, color, ignore_errors)
        self._display.display("----- FAILED ----", C.COLOR_ERROR)

    def v2_runner_on_ok(self, result):
        self._print_task_banner(result._task, head=True)

        color = C.COLOR_CHANGED if result._result.get('changed', False) \
            else C.COLOR_OK

        self.__display_result(result, color)

    def v2_runner_on_unreachable(self, result):
        del result._result["unreachable"] # no need for `__display_result` to tell that, we already do it here
        self._display.display(f"----- HOST UNREACHABLE ({result._host})----", C.COLOR_ERROR)
        self.__display_result(result, C.COLOR_VERBOSE, False)
        self._display.display("----- HOST UNREACHABLE ----", C.COLOR_ERROR)

    # items are handled as part of the 'normal' task logging
    def v2_runner_item_on_failed(self, result): pass
    def v2_runner_item_on_ok(self, result): pass
    def v2_runner_item_on_skipped(self, result): pass

    def _print_task_banner(self, task, head=False):
        if head:
            pass

            #self._display.display(f"{task}")

        else:
            self._display.display("")
            # followed by:
            "Monday 08 March 2021  10:38:44 +0100 (0:00:00.023)       0:00:06.476 **********"

    def v2_runner_retry(self, result):
        color = C.COLOR_VERBOSE

        if result._result['attempts'] == 1:
            self._display.display(f"{result._task}", color=color)
            self.__display_result(result, color)
            self._display.display("")

        self._display.display("---")
        self._display.display(str(result._task))
        self._display.display(f"{result._task.get_path().replace(os.getcwd()+'/', '')}", color=color)
        try:
            self.__print_cmd(result, color)
        except KeyError: pass # ignore

        self.__print_std_lines(result, "stdout", color)
        self.__print_std_lines(result, "stderr", color)
        self._display.display(f"==> failed attempt #{result._result['attempts']}/{result._task.retries}", color=color)


        self._display.display("")

    def v2_runner_on_start(self, host, task):
        pass

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._display.display("")
        self._display.display("~"*79)
        self._display.display(f"~~ {task.get_path().replace(os.getcwd()+'/', '')}")
        self._display.display(f"~~ {task}")

        self._display.display("~"*79)

        # followed by:
        "Friday 05 April 2024  15:01:14 +0200 (0:00:04.215)       0:00:04.504 **********"
