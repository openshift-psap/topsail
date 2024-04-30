from . import error_report
from ..store import prom
from . import prom_report
from . import lts_documentation
from . import sfttraining

def register():
    error_report.register()
    report.register()
    prom.register()
    prom_report.register()
    lts_documentation.register()
    sfttraining.register()
