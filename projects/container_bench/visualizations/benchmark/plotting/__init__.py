from . import power
from . import metrics
from . import report


def register():
    power.register()
    metrics.register()
    report.register()

