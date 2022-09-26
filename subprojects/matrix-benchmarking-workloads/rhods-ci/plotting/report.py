import copy

from dash import html
from dash import dcc

import matrix_benchmarking.plotting.table_stats as table_stats
import matrix_benchmarking.common as common

def register():
    PriceEstimationReport()
    UserExecutionOverviewReport()
    PodNodeMappingReport()
    LaunchAndExecTimeDistributionReport()
    NotebookPerformanceReport()


def set_vars(additional_settings, ordered_vars, settings, param_lists, variables, cfg):
    _settings = dict(settings)
    _variables = copy.deepcopy(variables)
    _ordered_vars = list(ordered_vars)
    for k, v in additional_settings.items():
        _settings[k] = v
        _variables.pop(k, True)
        if k in _ordered_vars:
            _ordered_vars.remove(k)

    _param_lists = [[(key, v) for v in variables[key]] for key in _ordered_vars]

    return _ordered_vars, _settings, _param_lists, _variables, cfg

def set_config(additional_cfg, args):
    cfg = copy.deepcopy(args[-1])
    cfg.d.update(additional_cfg)
    return list(args[:-1]) + [cfg]

def Plot(name, args, msg_p=None):
    stats = table_stats.TableStats.stats_by_name[name]
    fig, msg = stats.do_plot(*args)
    if msg_p is not None: msg_p.append(msg)

    return dcc.Graph(figure=fig)


class PodNodeMappingReport():
    def __init__(self):
        self.name = "report: Pod-Node Mapping"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.P("These plots show an overview of the mapping of the Pods on the different Nodes.")]
        header += [html.P("""The Timeline plots are useful to validate that Pods started and finished on time.""")]
        header += [html.P("""The Distribution plots are useful to visualize how the Pods were scheduled on the different Nodes.""")]

        for what in "Notebooks", "Test Pods":
            header += [html.H1(what)]

            header += [html.H2("Timeline")]
            header += [Plot(f"Pod/Node timeline: {what}", args)]
            header += [html.P(f"This plot shows the timeline of {what} mapping on the cluster's nodes, grouped by nodes. It can help understanding when the Pods started and finished their execution, as well as which users ran on the same node.")]

            header += [Plot(f"Pod/Node timeline: {what}", set_config(dict(force_order_by_user_idx=True),
                                                                         args))]
            header += [html.P(f"This plot shows the timeline of {what} mapping on the cluster's nodes, ordered by user ID. It can help understanding when the Pods started and finished their execution, as well as which users ran on the same node.")]

            header += html.Br()
            header += html.Br()

            header += [html.H2("Distribution")]
            header += [Plot(f"Pod/Node distribution: {what}", args)]
            header += [f"This plot shows the distribution of the {what} on the cluster's nodes. It provides the Node's name and machine-instance type."]

        return None, header

class UserExecutionOverviewReport():
    def __init__(self):
        self.name = "report: User Execution Overview"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H2("Execution Time of the User Steps")]
        header += [Plot("Notebook spawn time", args)]
        header += ["This plot shows the time the simulated user took to execute each of the test steps. User IDs shown in bold font failed to pass the test. Failed steps are not shown."]
        header += html.Br()
        header += html.Br()

        header += [html.H2("Execution Time with the failed steps")]
        header += [Plot(f"Notebook spawn time", set_config({"keep_failed_steps": True}, args))]
        header += ["This plot shows the time the simulated user took to execute each of the test steps. User IDs shown in bold font failed to pass the test. Failed steps _are_ shown."]

        header += [html.H2("Execution Time without the failed users")]
        header += [Plot(f"Notebook spawn time", set_config({"hide_failed_users": True}, args))]
        header += ["This plot shows the time the simulated user took to execute each of the test steps. User who failed the test are _not_ shown.."]

        return None, header

class PriceEstimationReport():
    def __init__(self):
        self.name = "report: Price Estimation"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args
        cnt = sum(1 for _ in common.Matrix.all_records(settings, setting_lists))
        if cnt != 1:
            return {}, f"ERROR: only one experiment must be selected. Found {cnt}."

        for entry in common.Matrix.all_records(settings, setting_lists):
            break

        header = []

        def add_price(user_count):
            nonlocal header
            header += [html.H2(f"Price to completion for {user_count} users")]
            if user_count == entry.results.user_count:
                header += [html.I("(current configuration)"), html.Br()]

            for mode in ["notebooks", "test_pods"]:
                header += [Plot("Price to completion",
                                set_config(dict(mode=mode, user_count=user_count), args))]

                header += [f"This plot shows an estimation of the price and number of machines required to run {user_count} {mode.replace('_', ' ')} simultaneously, for difference AWS instance types."]
                header += [html.Br()]
                header += [html.Br()]

        add_price(entry.results.user_count)

        for user_count in [5, 100, 300]:
            if user_count == entry.results.user_count: continue # don't show it twice
            add_price(user_count)

        return None, header

class LaunchAndExecTimeDistributionReport():
    def __init__(self):
        self.name = "report: Launch Time and Execution Time Distribution"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):

        header = []
        header += [html.P("These plots show the distribution of the user steps execution time and launch time.")]

        header += [html.H2("Start time distribution")]
        header += [Plot("Launch time distribution", args)]
        header += ["This plot provides information the start time of the different user steps. The failed steps are not taken into account."]
        header += [html.Br()]
        header += [html.Br()]


        header += [html.H2("Overview of the Execution time distribution")]
        header += [Plot("Execution time distribution", args)]
        header += ["This plot provides information about the execution timelength for the different user steps. The failed steps are not taken into account."]
        header += [html.Br()]
        header += [html.Br()]

        header += [html.H2("Execution time distribution for getting a usable Notebook")]

        msg_p = []
        header += [Plot("Execution time distribution",
                        set_config(dict(time_to_reach_step="Go to JupyterLab Page"), args),
                        msg_p,
                        )]
        header += [html.I(msg_p[0]), html.Br()]

        header += ["This plot provides information about the execution timelength required to reach JupyterLab front page. The failed steps are not taken into account."]
        header += [html.Br()]
        header += [html.Br()]


        header += ["The plots below show the break down of the execution timelength for the different steps."]

        ordered_vars, settings, setting_lists, variables, cfg = args
        for entry in common.Matrix.all_records(settings, setting_lists):
            break


        step_names = []
        for ods_ci_output in entry.results.ods_ci_output.values():
            step_names = list(ods_ci_output.keys())
            break

        for step_name in step_names:
            if step_name == "Open the Browser": continue

            msg_p=[]
            header += [Plot("Execution time distribution",
                            set_config(dict(step=step_name), args),
                            msg_p)]
            header += [html.I(msg_p[0])]
            header += [html.Br(), html.Br()]

        return None, header


class NotebookPerformanceReport():
    def __init__(self):
        self.name = "report: Notebook Performance"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True
        self.is_report = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        header = []
        header += [html.H2("Notebook Performance")]
        msg_p = []
        header += [Plot("Notebook Performance", set_config(dict(all_in_one=True), args), msg_p)]
        header += [html.I(msg_p[0]), html.Br()]

        header += ["This plot shows the distribution of the notebook performance benchmark results, for all of the simulated users."]
        header += html.Br()
        header += html.Br()

        msg_p = []
        header += [Plot("Notebook Performance", args, msg_p)]
        header += [html.I(msg_p[0]), html.Br()]
        header += ["This plot shows the distribution of the notebook performance benchmark results, for each of the simulated users."]

        header += html.Br()
        header += html.Br()

        return None, header
