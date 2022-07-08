*** Settings ***
Resource            tests/Resources/ODS.robot
Resource            tests/Resources/Common.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterHubSpawner.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterLabLauncher.robot
Library             DebugLibrary
Library             JupyterLibrary
Library             libs/Helpers.py

*** Variables ***

${NOTEBOOK_IMAGE_NAME}         s2i-generic-data-science-notebook
${NOTEBOOK_IMAGE_SIZE}         Default
${NOTEBOOK_SPAWN_WAIT_TIME}    5 minutes

${NOTEBOOK_URL}       %{NOTEBOOK_URL}
${NOTEBOOK_NAME}      notebook.ipynb


*** Keywords ***

Setup
  Set Library Search Order  SeleniumLibrary
  RHOSi Setup
  Open Browser  ${ODH_DASHBOARD_URL}  browser=${BROWSER.NAME}  options=${BROWSER.OPTIONS}


*** Test Cases ***

Open the Browser
  [Tags]  Setup
  Setup

Go to RHODS Dashboard
  [Tags]  Authenticate

  Login To RHODS Dashboard  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}
  Wait for RHODS Dashboard to Load
  Capture Page Screenshot


Go to JupyterHub
  [Tags]  Authenticate

  Launch JupyterHub From RHODS Dashboard Link
  Login To Jupyterhub  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}
  ${authorization_required} =  Is Service Account Authorization Required
  Run Keyword If  ${authorization_required}  Authorize jupyterhub service account
  Wait Until Page Contains Element    xpath://span[@id='jupyterhub-logo']
  Capture Page Screenshot


Spawn a Notebook
  [Tags]  Spawn  Notebook

  Fix Spawner Status
  Spawn Notebook With Arguments  image=s2i-generic-data-science-notebook  size=Default  spawner_timeout=${NOTEBOOK_SPAWN_WAIT_TIME}
  Capture Page Screenshot

Load the Notebook
  [Tags]  Notebook

  ${is_launcher_selected} =  Run Keyword And Return Status  JupyterLab Launcher Tab Is Selected
  Capture Page Screenshot
  Run Keyword If  not ${is_launcher_selected}  Open JupyterLab Launcher
  Capture Page Screenshot
  Launch a new JupyterLab Document
  Close Other JupyterLab Tabs
  Capture Page Screenshot
  Run Cell And Check For Errors  !curl "${NOTEBOOK_URL}" > "${NOTEBOOK_NAME}"
  Wait Until JupyterLab Code Cell Is Not Active  timeout=300

  Capture Page Screenshot

  Open With JupyterLab Menu  File  Open from Path…
  Input Text  xpath=//input[@placeholder="/path/relative/to/jlab/root"]  ${NOTEBOOK_NAME}
  Click Element  xpath://div[.="Open"]
  Wait Until ${NOTEBOOK_NAME} JupyterLab Tab Is Selected
  Close Other JupyterLab Tabs
  Capture Page Screenshot


Run the Notebook
  [Tags]  Notebook

  Open With JupyterLab Menu  Run  Run All Cells
  Capture Page Screenshot

  Wait Until JupyterLab Code Cell Is Not Active  timeout=300
  Capture Page Screenshot
