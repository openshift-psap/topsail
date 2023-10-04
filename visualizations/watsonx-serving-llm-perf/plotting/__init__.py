from . import report
from . import latency

def register():
    report.register()
    latency.register()
