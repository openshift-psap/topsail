from enum import auto

import matrix_benchmarking.models as models

from pydantic import ConstrainedStr

class StepName(models.PSAPEnum):
    Open_the_Browser = auto()
    Login_to_RHODS_Dashboard = auto()
    Go_to_RHODS_Dashboard = auto()
    Go_to_the_Project_page = auto()
    Create_and_Start_the_Workbench = auto()
    Login_to_JupyterLab_Page = auto()
    Go_to_JupyterLab_Page = auto()
    Load_the_Notebook = auto()
    Run_the_Notebook = auto()

class StepStatus(models.PSAPEnum):
    PASS = auto()
    FAIL = auto()

class TestName(models.PSAPEnum):
    rhods_notebooks_ux = 'rhods-notebooks-ux'
