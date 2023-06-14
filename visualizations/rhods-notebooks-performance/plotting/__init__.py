from . import report
from . import notebook_performance_comparison
from . import gating_report
from . import notebook_performance

def register():
    report.register()
    notebook_performance_comparison.register()
    gating_report.register()
    notebook_performance.register()
