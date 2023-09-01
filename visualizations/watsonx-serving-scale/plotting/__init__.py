from . import error_report
from ..store import prom
from . import prom_report
from . import user_progress

def register():
    error_report.register()
    report.register()
    prom.register()
    prom_report.register()
    user_progress.register()
