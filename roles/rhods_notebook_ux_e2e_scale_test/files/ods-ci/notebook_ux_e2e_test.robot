*** Settings ***
Resource            tests/Resources/ODS.robot
Resource            tests/Resources/Common.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterHubSpawner.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterLabLauncher.robot
Library             JupyterLibrary
Library             libs/Helpers.py
Library             SeleniumLibrary

Suite Teardown  Tear Down

*** Variables ***

${NOTEBOOK_IMAGE_NAME}         %{NOTEBOOK_IMAGE_NAME}
# needs to match ODS_NOTEBOOK_SIZE in testing/ods/notebook_ux_e2e_scale_test.sh
${NOTEBOOK_IMAGE_SIZE}         default
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
  Open Browser  ${ODH_DASHBOARD_URL}  browser=${BROWSER.NAME}  options=${BROWSER.OPTIONS}  desired_capabilities=${capabilities}

Tear Down
  Capture Page Screenshot
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
  Wait for Dashboard to Load
  Capture Page Screenshot

Go to Jupyter
  [Tags]  Authenticate

  Launch Jupyter From RHODS Dashboard Link
  Wait Until Page Contains  Start a notebook server
  Wait Until Page Contains  Start server
  Capture Page Screenshot


Spawn a Notebook
  [Tags]  Spawn  Notebook

  Select Notebook Image  ${NOTEBOOK_IMAGE_NAME}
  Select Container Size  ${NOTEBOOK_IMAGE_SIZE}

  Capture Page Screenshot

  Custom Spawn Notebook
  Capture Page Screenshot


Go to JupyterLab Page
  [Tags]  Spawn  Notebook

  Login To JupyterLab  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}
  Wait Until Page Contains Element  xpath://img[@class="jp-Launcher-kernelIcon"]  timeout=60s
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
  ${has_errors}  ${error}=  Run Keyword And Ignore Error  Get JupyterLab Code Cell Error Text

  IF  '${has_errors}' == 'PASS'
      Log  ${error}
      Fail  "Error detected during the execution of the notebook:\n${error}"
  END


*** Keywords ***
Get Browser Console Log Entries
    ${selenium}=    Get Library Instance    SeleniumLibrary
    ${webdriver}=    Set Variable     ${selenium._drivers.active_drivers}[0]
    ${log entries}=    Evaluate    $webdriver.get_log('browser')
    [Return]    ${log entries}

Login To JupyterLab
   [Arguments]  ${ocp_user_name}  ${ocp_user_pw}  ${ocp_user_auth_type}

   ${oauth_prompt_visible} =  Is OpenShift OAuth Login Prompt Visible
   Run Keyword If  ${oauth_prompt_visible}  Click Button  Log in with OpenShift
   ${login-required} =  Is OpenShift Login Visible
   Run Keyword If  ${login-required}  Login To Openshift  ${ocp_user_name}  ${ocp_user_pw}  ${ocp_user_auth_type}
   ${authorize_service_account} =  Is jupyter-nb-${TEST_USER.USERNAME} Service Account Authorization Required
   # correct name not required/not working, not sure why
   Run Keyword If  ${authorize_service_account}  Authorize rhods-dashboard service account

Wait for Dashboard to Load

    Wait Until Page Contains  Launch your enabled applications

# wait only 35s
Custom Spawn Notebook
    [Documentation]  Start the notebook pod spawn and wait ${spawner_timeout} seconds (DEFAULT: 600s)
    [Arguments]  ${spawner_timeout}=600 seconds
    Click Button  Start server
    Wait Until Page Contains  Starting server  35s
    Wait Until Element Is Visible  xpath://div[@role="progressbar"]
    Wait Until Page Does Not Contain Element  xpath://div[@role="progressbar"]  ${spawner_timeout}
