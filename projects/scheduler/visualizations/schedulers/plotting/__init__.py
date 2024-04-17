from . import error_report
from ..store import prom
from . import prom_report
from . import resource_allocation
from . import resource_creation
from . import mapping
from . import time_distribution
from . import progress
from . import compare_test_speed
from . import compare_report
from . import scheduling
from . import lts_documentation

def register():
    error_report.register()
    report.register()
    prom.register()
    prom_report.register()
    resource_allocation.register()
    resource_creation.register()
    mapping.register()
    time_distribution.register()
    progress.register()
    compare_test_speed.register()
    compare_report.register()
    scheduling.register()
    lts_documentation.register()
