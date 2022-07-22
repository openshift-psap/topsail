*** Settings ***
Resource            tests/Resources/ODS.robot
Resource            tests/Resources/Common.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterHubSpawner.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterLabLauncher.robot
Library             DebugLibrary
Library             JupyterLibrary
Library             libs/Helpers.py
Library             SeleniumLibrary

Suite Teardown  Tear Down

*** Variables ***

${NOTEBOOK_IMAGE_NAME}         s2i-generic-data-science-notebook
${NOTEBOOK_IMAGE_SIZE}         Default
${NOTEBOOK_SPAWN_WAIT_TIME}    15 minutes
${NOTEBOOK_SPAWN_RETRIES}      45
${NOTEBOOK_SPAWN_RETRY_DELAY}  20 seconds

${NOTEBOOK_URL}                %{NOTEBOOK_URL}
${NOTEBOOK_NAME}               notebook.ipynb
${NOTEBOOK_CLONE_WAIT_TIME}    30 seconds
${NOTEBOOK_EXEC_WAIT_TIME}     5 minutes

&{browser logging capability}    browser=ALL
&{capabilities}    browserName=chrome    version=${EMPTY}    platform=ANY    goog:loggingPrefs=${browser logging capability}

*** Keywords ***

Setup
  Set Library Search Order  SeleniumLibrary
  RHOSi Setup
  Open Browser  ${ODH_DASHBOARD_URL}  browser=${BROWSER.NAME}  options=${BROWSER.OPTIONS}  desired_capabilities=${capabilities}

Tear Down
  ${browser log entries}=    Get Browser Console Log Entries
  Log    ${browser log entries}
  ${browser log entries str}=   Convert To String  ${browser log entries}
  Create File  ${OUTPUTDIR}/browser_log_entries.yaml  ${browser log entries str}

  Close Browser

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
  Spawn Notebook With Arguments  image=${NOTEBOOK_IMAGE_NAME}  size=${NOTEBOOK_IMAGE_SIZE}  spawner_timeout=${NOTEBOOK_SPAWN_WAIT_TIME}  retries=${NOTEBOOK_SPAWN_RETRIES}  retries_delay=${NOTEBOOK_SPAWN_RETRY_DELAY}
  Capture Page Screenshot

Load the Notebook
  [Tags]  Notebook

  ${is_launcher_selected} =  Run Keyword And Return Status  JupyterLab Launcher Tab Is Selected
  Run Keyword If  not ${is_launcher_selected}  Open JupyterLab Launcher
  Capture Page Screenshot
  Launch a new JupyterLab Document
  Close Other JupyterLab Tabs
  Run Cell And Check For Errors  !curl "${NOTEBOOK_URL}" -o "${NOTEBOOK_NAME}"
  Wait Until JupyterLab Code Cell Is Not Active  timeout=${NOTEBOOK_CLONE_WAIT_TIME}
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

  Wait Until JupyterLab Code Cell Is Not Active  timeout=${NOTEBOOK_EXEC_WAIT_TIME}
  Capture Page Screenshot

*** Keywords ***
Get Browser Console Log Entries
    ${selenium}=    Get Library Instance    SeleniumLibrary
    ${webdriver}=    Set Variable     ${selenium._drivers.active_drivers}[0]
    ${log entries}=    Evaluate    $webdriver.get_log('browser')
    [Return]    ${log entries}
