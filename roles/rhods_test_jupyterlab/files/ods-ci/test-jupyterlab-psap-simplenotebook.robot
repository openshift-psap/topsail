*** Settings ***
Resource            tests/Resources/ODS.robot
Resource            tests/Resources/Common.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterHubSpawner.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterLabLauncher.robot
Library             DebugLibrary
Library             JupyterLibrary
Library             libs/Helpers.py

Suite Setup         Begin Web Test
Suite Teardown      End Web Test

Force Tags          Smoke    Sanity    JupyterHub

*** Variables ***

*** Test Cases ***
Open RHODS Dashboard
    [Tags]  RHODS

    Wait for RHODS Dashboard to Load

Can Launch Jupyterhub
    [Tags]  Jupyterhub
    ${version-check} =    Is RHODS Version Greater Or Equal Than    1.4.0
    IF    ${version-check}==True
        Launch JupyterHub From RHODS Dashboard Link
    ELSE
        Launch JupyterHub From RHODS Dashboard Dropdown
    END

Can Login to Jupyterhub
    [Tags]  Jupyterhub
    Login To Jupyterhub    ${TEST_USER.USERNAME}    ${TEST_USER.PASSWORD}    ${TEST_USER.AUTH_TYPE}
    ${authorization_required} =    Is Service Account Authorization Required
    Run Keyword If    ${authorization_required}    Authorize jupyterhub service account
    Wait Until Page Contains Element    xpath://span[@id='jupyterhub-logo']

Can Spawn Notebook
  [Tags]  Notebook
  Fix Spawner Status
  Spawn Notebook With Arguments  image=s2i-generic-data-science-notebook  size=Default  spawner_timeout=5 minutes

Git Clone the PSAP notebooks
  [Tags]  Notebook
  Capture Page Screenshot
  ${is_launcher_selected} =  Run Keyword And Return Status  JupyterLab Launcher Tab Is Selected
  Run Keyword If  not ${is_launcher_selected}  Open JupyterLab Launcher
  Launch a new JupyterLab Document
  Add and Run JupyterLab Code Cell in Active Notebook  !rm -rf ~/RHODS-Jupyter-Notebooks/
  Close Other JupyterLab Tabs
  Capture Page Screenshot
  Navigate Home (Root folder) In JupyterLab Sidebar File Browser
  Open With JupyterLab Menu  Git  Clone a Repository
  Input Text  //div[.="Clone a repo"]/../div[contains(@class, "jp-Dialog-body")]//input  https://github.com/openshift-psap/RHODS-Jupyter-Notebooks.git
  Click Element  xpath://div[.="CLONE"]
  Capture Page Screenshot

Run the PSAP jh-at-scale Simple Notebook
  [Tags]  Notebook

  Capture Page Screenshot
  Open With JupyterLab Menu  File  Open from Path…
  Input Text  xpath=//input[@placeholder="/path/relative/to/jlab/root"]  RHODS-Jupyter-Notebooks/jh-at-scale/simple-notebook.ipynb
  Click Element  xpath://div[.="Open"]
  Wait Until simple-notebook.ipynb JupyterLab Tab Is Selected

  Close Other JupyterLab Tabs
  Capture Page Screenshot
  Open With JupyterLab Menu  Run  Run All Cells
  Capture Page Screenshot

  ## because the test will take 1 minute
  Wait Until JupyterLab Code Cell Is Not Active  timeout=300
  Capture Page Screenshot
  Run Cell And Check Output  print("done")  done
  Capture Page Screenshot
  JupyterLab Code Cell Error Output Should Not Be Visible
  ${output} =  Get Text  (//div[contains(@class,"jp-OutputArea-output")])[last()]
  Should Not Match  ${output}  ERROR*
  Capture Page Screenshot

Can Close Notebook when done
  [Tags]  Notebook  End Sequence
  Stop JupyterLab Notebook Server
  # Capture Page Screenshot
  # Go To  ${ODH_DASHBOARD_URL}
  Capture Page Screenshot
