from . import metrics
from . import report
from . import comparison_report


def register():
    metrics.register()
    report.register()
    comparison_report.register()
