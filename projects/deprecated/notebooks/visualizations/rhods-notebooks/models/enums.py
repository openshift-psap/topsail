from enum import auto

import matrix_benchmarking.models as matbench_models

from pydantic import ConstrainedStr

class StepName(matbench_models.PSAPEnum):
    Open_the_Browser = auto()
    Login_to_RHODS_Dashboard = auto()
    Go_to_RHODS_Dashboard = auto()
    Go_to_the_Project_page = auto()
    Go_to_Jupyter_Page = auto()
    Wait_for_the_Notebook_Spawn = auto()
    Create_and_Start_the_Workbench = auto()
    Login_to_JupyterLab_Page = auto()
    Go_to_JupyterLab_Page = auto()
    Load_the_Notebook = auto()
    Run_the_Notebook = auto()

class StepStatus(matbench_models.PSAPEnum):
    PASS = auto()
    FAIL = auto()
