from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

from . import completion
from . import report
from . import mapping
from . import spawntime
from . import status
from . import launch_time
from . import error_report
from . import prom_report
from . import notebook_performance
from . import perf_report
from . import multi_notebook_spawn_time
from . import gating_report
from . import lts_documentation

from ..store import prom

def register():
    completion.register()
    report.register()
    mapping.register()
    spawntime.register()
    status.register()
    launch_time.register()
    error_report.register()
    prom_report.register()
    notebook_performance.register()
    perf_report.register()
    multi_notebook_spawn_time.register()
    gating_report.register()
    lts_documentation.register()
    prom.register()
