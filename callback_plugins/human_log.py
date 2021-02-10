from ansible.plugins.callback.default import CallbackModule as default_CallbackModule
from ansible import constants as C

# extends this class: https://github.com/ansible/ansible/blob/devel/lib/ansible/plugins/callback/default.py

INTERESTING_MODULE_PROPS = {
    "stat": ["path", "exists", "mode"],
    "invocation": None,
    "_ansible_no_log": None,
    "_ansible_verbose_always": None,
    "__ansible_verbose_override": None,
    "msg": None,
    "changed": None,
    "ansible_facts": None,
    "include_args": None
    }

class CallbackModule(default_CallbackModule):
    def __display_result(self, result, color, ignore_errors=None):
        self._display.display(f"{result._task}", color=color)
        if ignore_errors is not None:
            self._display.display(f"==> FAILED | ignore_errors={ignore_errors}", color=color)


        try: self._display.display(f"msg: {result._result['msg']}", color=color)
        except KeyError: pass

        try: self._display.display(f"changed: {result._result['changed']}", color=color)
        except KeyError: pass

        try:
            cmd = result._result['cmd']

            str_cmd = cmd if isinstance(cmd, str) \
                else ' '.join(cmd)

            self._display.display(f"", color=color)
            self._display.display(f"<command> {str_cmd}", color=color)
            self._display.display(f"", color=color)

        except KeyError:
            def print_dict(key, d, depth=1):
                for k, v in d.items():
                    if k in INTERESTING_MODULE_PROPS:
                        if INTERESTING_MODULE_PROPS[k] is None: continue
                        if v not in INTERESTING_MODULE_PROPS[k]: continue
                    if not isinstance(v, dict):
                        self._display.display(f"{'  '*depth}- {k}:\t{v}", color=C.COLOR_VERBOSE)
                    else:
                        self._display.display(f"{'  '*depth}- {k}", color=C.COLOR_VERBOSE)
                        print_dict(k, v, depth+1)

            print_dict("_top", result._result)
            # ^^^ will print stdout and stderr
            return

        ####

        self.__print_std_lines(result, "stdout", color)
        self.__print_std_lines(result, "stderr", color)

    def __print_std_lines(self, result, std_name, color):
        if not result._result[f'{std_name}_lines']:
            return

        for line in result._result[f'{std_name}_lines']:
            self._display.display(f"<{std_name}> {line}", color=color)

    def v2_runner_on_skipped(self, result):
        self._display.display(f"{result._task}", color=C.COLOR_SKIP)
        self._display.display(f"==> SKIPPED | {result._result.get('skip_reason', '(no reason provided)')}",
                              color=C.COLOR_SKIP)
        for condition in result._task.when:
            self._display.display(f"when: {condition}", C.COLOR_SKIP)


    def v2_runner_on_failed(self, result, ignore_errors=False):
        color = C.COLOR_VERBOSE if ignore_errors else C.COLOR_ERROR

        self.__display_result(result, color, ignore_errors)

    def v2_runner_on_ok(self, result):
        color = C.COLOR_CHANGED if result._result.get('changed', False) \
            else C.COLOR_OK

        self.__display_result(result, color)

    def _print_task_banner(self, task):
        self._display.display("---")
        self._display.display("")
        self._display.display(f"{task.get_path()}")

        pass

    def v2_runner_retry(self, result):
        color = C.COLOR_VERBOSE

        if result._result['attempts'] == 1:
            self._display.display(f"{result._task}", color=color)
            self.__display_result(result, color)
            self._display.display("")

        self._display.display(f"==> FAILED attempt #{result._result['attempts']}/{result._task.retries}", color=color)

        self.__print_std_lines(result, "stdout", color)
        self.__print_std_lines(result, "stderr", color)
        self._display.display("")

    def v2_runner_on_start(self, host, task): pass
