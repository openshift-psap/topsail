from . import error_report
from ..store import prom
from . import prom_report
from . import user_progress
from . import resource_creation
from . import grpc_distribution
from . import conditions
from . import load_time
from . import lts_documentation

def register():
    error_report.register()
    report.register()
    prom.register()
    prom_report.register()
    user_progress.register()
    resource_creation.register()
    grpc_distribution.register()
    conditions.register()
    load_time.register()
    lts_documentation.register()
