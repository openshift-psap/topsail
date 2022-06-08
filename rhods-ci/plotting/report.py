import copy

from dash import html
from dash import dcc

from matrix_benchmarking.common import Matrix
import matrix_benchmarking.plotting.table_stats as table_stats

def register():
    ExecutionOverviewReport()
    PriceOverviewReport()

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

class ExecutionOverviewReport():
    def __init__(self):
        self.name = "Execution overview"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        timeline = table_stats.TableStats.stats_by_name['Timeline']
        testpod_cpu_usage = table_stats.TableStats.stats_by_name['Prom: Test Pod CPU usage']
        testpod_memory_usage = table_stats.TableStats.stats_by_name['Prom: Test Pod memory usage']

        header = []
        header += [html.H2("Timeline")]
        header += [dcc.Graph(figure=timeline.do_plot(*args)[0])]

        header += [html.H2("Test pod CPU usage")]
        header += [dcc.Graph(figure=testpod_cpu_usage.do_plot(*args)[0])]

        header += [html.H2("Test pod memory usage")]
        header += [dcc.Graph(figure=testpod_memory_usage.do_plot(*args)[0])]

        return None, header

class PriceOverviewReport():
    def __init__(self):
        self.name = "Price overview"
        self.id_name = self.name.lower().replace(" ", "_")
        self.no_graph = True

        table_stats.TableStats._register_stat(self)

    def do_plot(self, *args):
        ordered_vars, settings, setting_lists, variables, cfg = args

        timeline = table_stats.TableStats.stats_by_name['Price to completion']
        if "notebook_size" in ordered_vars:
            ordered_vars.remove("notebook_size")

        report = []
        for notebook_size in variables.get("notebook_size", [settings["notebook_size"]]):
            additional_settings = dict(
                notebook_size=notebook_size
            )
            report += [html.H2(f"Price for size={notebook_size}")]

            report += [dcc.Graph(figure=timeline.do_plot(*set_vars(additional_settings, *args))[0])]


        return None, report
