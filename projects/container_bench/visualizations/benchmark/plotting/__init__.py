from . import power
from . import metrics


def register():
    power.register()
    metrics.register()
