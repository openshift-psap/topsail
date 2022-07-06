*** Settings ***
Resource            tests/Resources/ODS.robot
Resource            tests/Resources/Common.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterHubSpawner.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterLabLauncher.robot
Library             DebugLibrary
Library             JupyterLibrary
Library             libs/Helpers.py

Force Tags          Smoke    Sanity    JupyterHub

*** Variables ***
${REPOSITORY_NAME}    RHODS-Jupyter-Notebooks
${NOTEBOOK_GIT_REPOSITORY}     https://github.com/openshift-psap/${REPOSITORY_NAME}.git
${NOTEBOOK_PATH}      jh-at-scale
${NOTEBOOK_NAME}      simple-notebook.ipynb

${NOTEBOOK_IMAGE_NAME}    s2i-generic-data-science-notebook
${NOTEBOOK_IMAGE_SIZE}    Default
${NOTEBOOK_SPAWN_WAIT_TIME}    5 minutes
*** Test Cases ***

Begin and Authenticate
  Begin and Authenticate

Login to Jupyterhub
  [Tags]  Jupyterhub

  ${authorization_required} =    Is Service Account Authorization Required
  Run Keyword If    ${authorization_required}    Authorize jupyterhub service account

Spawn a Notebook
  [Tags]  Notebook

  Wait Until Page Contains Element    xpath://span[@id='jupyterhub-logo']
  Fix Spawner Status
  Spawn Notebook With Arguments  image=${NOTEBOOK_IMAGE_NAME}  size=${NOTEBOOK_IMAGE_SIZE}  spawner_timeout=${NOTEBOOK_SPAWN_WAIT_TIME}

Git Clone the PSAP notebooks
  [Tags]  Notebook
  Capture Page Screenshot
  ${is_launcher_selected} =  Run Keyword And Return Status  JupyterLab Launcher Tab Is Selected
  Run Keyword If  not ${is_launcher_selected}  Open JupyterLab Launcher
  Launch a new JupyterLab Document
  Add and Run JupyterLab Code Cell in Active Notebook  !rm -rf ~/${REPOSITORY_NAME}/
  Close Other JupyterLab Tabs
  Capture Page Screenshot
  Navigate Home (Root folder) In JupyterLab Sidebar File Browser
  Open With JupyterLab Menu  Git  Clone a Repository
  Input Text  //div[.="Clone a repo"]/../div[contains(@class, "jp-Dialog-body")]//input  ${NOTEBOOK_GIT_REPOSITORY}
  Click Element  xpath://div[.="CLONE"]
  Capture Page Screenshot

Run the PSAP jh-at-scale Simple Notebook
  [Tags]  Notebook

  Capture Page Screenshot
  Open With JupyterLab Menu  File  Open from Path…
  Input Text  xpath=//input[@placeholder="/path/relative/to/jlab/root"]  ${REPOSITORY_NAME}/${NOTEBOOK_PATH}/${NOTEBOOK_NAME}
  Click Element  xpath://div[.="Open"]
  Wait Until ${NOTEBOOK_NAME} JupyterLab Tab Is Selected

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

*** Keywords ***

Begin and Authenticate
  Set Library Search Order  SeleniumLibrary
  RHOSi Setup

  Open Browser  ${ODH_DASHBOARD_URL}  browser=${BROWSER.NAME}  options=${BROWSER.OPTIONS}
  Login To RHODS Dashboard  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}
  Wait for RHODS Dashboard to Load
  Launch JupyterHub From RHODS Dashboard Link
  Login To Jupyterhub  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}
  ${authorization_required} =  Is Service Account Authorization Required
  Run Keyword If  ${authorization_required}  Authorize jupyterhub service account
  Fix Spawner Status
