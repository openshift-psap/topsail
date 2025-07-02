from . import metrics
from . import report


def register():
    metrics.register()
    report.register()
