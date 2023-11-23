*** Settings ***
Resource            tests/Resources/ODS.robot
Resource            tests/Resources/Common.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterHubSpawner.robot
Resource            tests/Resources/Page/ODH/JupyterHub/JupyterLabLauncher.robot
Library             JupyterLibrary
Library             libs/Helpers.py
Library             SeleniumLibrary
# Library             DebugLibrary  # then use the 'Debug' keyword to set a breakpoint

Suite Teardown  Tear Down

Resource  notebook_scale_test_common.resource

*** Variables ***

${DASHBOARD_PRODUCT_NAME}      "%{DASHBOARD_PRODUCT_NAME}"

${NOTEBOOK_IMAGE_NAME}         %{NOTEBOOK_IMAGE_NAME}

${NOTEBOOK_BENCHMARK_NAME}     %{NOTEBOOK_BENCHMARK_NAME}
${NOTEBOOK_BENCHMARK_NUMBER}   %{NOTEBOOK_BENCHMARK_NUMBER}
${NOTEBOOK_BENCHMARK_REPEAT}   %{NOTEBOOK_BENCHMARK_REPEAT}

${NOTEBOOK_IMAGE_SIZE}         %{NOTEBOOK_SIZE_NAME}
${NOTEBOOK_SPAWN_WAIT_TIME}    20 minutes

${NOTEBOOK_URL}                %{NOTEBOOK_URL}
${NOTEBOOK_CLONE_WAIT_TIME}    3 minutes
${NOTEBOOK_EXEC_WAIT_TIME}     1 minutes

*** Test Cases ***

Open the Browser
  [Tags]  Setup

  Initialize Global Variables
  Setup

Login to RHODS Dashboard
  [Tags]  Authenticate

  Go To  ${ODH_DASHBOARD_URL}
  Login To RHODS Dashboard  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}


Go to RHODS Dashboard
  [Tags]  Dashboard

  Wait For Condition  return document.title == ${DASHBOARD_PRODUCT_NAME}  timeout=3 minutes
  Wait Until Page Contains  Launch application  timeout=60 seconds
  Capture Page Screenshot


Go to Jupyter Page
  [Tags]  Dashboard  Notebook  Spawn

  Launch Jupyter From RHODS Dashboard Link
  Wait Until Page Contains  Start a notebook server  timeout=60 seconds
  Wait Until Page Contains  Start server  timeout=60 seconds
  Capture Page Screenshot

  Select Notebook Image  ${NOTEBOOK_IMAGE_NAME}
  Select Container Size  ${NOTEBOOK_IMAGE_SIZE}

  Capture Page Screenshot


Wait for the Notebook Spawn
  [Tags]  Notebook  Wait

  # nothing to do for %{TEST_ONLY_CREATE_NOTEBOOKS} == True, as this test and the followings are skipped

  Trigger Notebook Spawn

  Wait Notebook Spawn  ${NOTEBOOK_SPAWN_WAIT_TIME}
  Capture Page Screenshot


Login to JupyterLab Page
  [Tags]  Notebook  JupyterLab

  Login To JupyterLab  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}


Go to JupyterLab Page
  [Tags]  Notebook  JupyterLab

  Wait Until Page Contains Element  xpath:${JL_TABBAR_CONTENT_XPATH}  timeout=3 minutes
  Capture Page Screenshot


Load the Notebook
  [Tags]  Notebook  JupyterLab

  Load the Notebook


Run the Notebook
  [Tags]  Notebook  JupyterLab

  Run the Notebook


*** Keywords ***


Trigger Notebook Spawn
  [Arguments]  ${modal_timeout}=60 seconds

  ${rhods_17_or_above}=  Is RHODS Version Greater Or Equal Than  1.17.0
  IF  ${rhods_17_or_above} == True
      ${notebook_browser_tab_preference}=  Set Variable  //input[@id="checkbox-notebook-browser-tab-preference"]
      ${new_tab_checked}  Get Element Attribute  ${notebook_browser_tab_preference}  checked
      Run Keyword If  "${new_tab_checked}" == "${None}"  Click Element  xpath://input[@id="checkbox-notebook-browser-tab-preference"]
  END
  Click Button  Start server
  Wait Until Page Contains  Starting server  ${modal_timeout}
  Wait Until Element Is Visible  xpath://div[@role="progressbar"]


Wait Notebook Spawn
  [Arguments]  ${spawner_timeout}=600 seconds

  Wait Until Page Does Not Contain Element  xpath://div[@role="progressbar"]  ${spawner_timeout}
