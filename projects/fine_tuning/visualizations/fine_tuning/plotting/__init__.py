from . import error_report
from . import lts_documentation
from . import sfttrainer

def register():
    error_report.register()
    report.register()
    lts_documentation.register()
    sfttrainer.register()
