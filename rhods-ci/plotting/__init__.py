from collections import defaultdict

import plotly.graph_objs as go
import pandas as pd
import plotly.express as px

from . import simple_timeline
from . import advanced_timeline

def register():
    simple_timeline.register()
    advanced_timeline.register()
