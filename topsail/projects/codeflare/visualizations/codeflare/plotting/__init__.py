from . import error_report
from ..store import prom
from . import prom_report
from . import resource_allocation
from . import mapping
from . import time_distribution
from . import progress
from . import compare_test_speed
from . import compare_report

def register():
    error_report.register()
    report.register()
    prom.register()
    prom_report.register()
    resource_allocation.register()
    mapping.register()
    time_distribution.register()
    progress.register()
    compare_test_speed.register()
    compare_report.register()
