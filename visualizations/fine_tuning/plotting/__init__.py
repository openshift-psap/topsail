from . import error_report
from . import sfttrainer
from . import ray_benchmark
from . import ilab_training

import projects.matrix_benchmarking.visualizations.helpers.plotting.lts_documentation as lts_documentation
import projects.matrix_benchmarking.visualizations.helpers.plotting.kpi_table as kpi_table
import projects.matrix_benchmarking.visualizations.helpers.plotting.kpi_plot as kpi_plot

def register():
    error_report.register()
    report.register()
    lts_documentation.register()
    sfttrainer.register()
    ray_benchmark.register()
    ilab_training.register()
    kpi_table.register()
    kpi_plot.register()

