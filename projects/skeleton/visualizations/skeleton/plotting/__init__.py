from . import error_report
from ..store import prom
from . import prom_report

import projects.matrix_benchmarking.visualizations.helpers.plotting.lts_documentation as lts_documentation

def register():
    error_report.register()
    report.register()
    prom.register()
    prom_report.register()
    lts_documentation.register()
