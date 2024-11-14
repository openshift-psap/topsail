from . import error_report
from . import sfttrainer
from . import ray_benchmark

import projects.matrix_benchmarking.visualizations.helpers.plotting.lts_documentation as lts_documentation
import projects.matrix_benchmarking.visualizations.helpers.plotting.kpi_table as kpi_table

def register():
    error_report.register()
    report.register()
    lts_documentation.register()
    sfttrainer.register()
    kpi_table.register()
    ray_benchmark.register()
