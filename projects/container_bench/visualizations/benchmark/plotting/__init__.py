from . import metrics
from . import report
from . import comparison_report
from . import comparison_plots


def register():
    metrics.register()
    report.register()
    comparison_plots.register()
    comparison_report.register()
