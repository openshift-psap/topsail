from . import report
from . import notebook_performance_comparison
from . import gating_report
from . import notebook_performance

import projects.matrix_benchmarking.visualizations.helpers.plotting.lts_documentation as lts_documentation

def register():
    report.register()
    notebook_performance_comparison.register()
    gating_report.register()
    notebook_performance.register()
    lts_documentation.register()
