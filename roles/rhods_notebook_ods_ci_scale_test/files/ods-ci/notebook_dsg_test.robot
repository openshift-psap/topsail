*** Settings ***
Resource            tests/Resources/ODS.robot
Resource            tests/Resources/Common.robot
Resource            tests/Resources/Page/ODH/ODHDashboard/ODHDataScienceProject/Workbenches.resource
Resource            tests/Resources/Page/ODH/ODHDashboard/ODHDataScienceProject/Projects.resource

Library             JupyterLibrary
Library             libs/Helpers.py
Library             SeleniumLibrary
#Library             DebugLibrary  # then use the 'Debug' keyword to set a breakpoint

Resource  notebook_scale_test_common.resource

Suite Teardown  Tear Down

*** Variables ***

${DASHBOARD_PRODUCT_NAME}      "%{DASHBOARD_PRODUCT_NAME}"

${PROJECT_NAME}                ${TEST_USER.USERNAME}
${WORKBENCH_NAME}              ${TEST_USER.USERNAME}

${NOTEBOOK_IMAGE_NAME_DESCR}   %{NOTEBOOK_IMAGE_NAME_DESCR}
${NOTEBOOK_SIZE_NAME}          %{NOTEBOOK_SIZE_NAME}

${NOTEBOOK_BENCHMARK_NAME}     %{NOTEBOOK_BENCHMARK_NAME}
${NOTEBOOK_BENCHMARK_NUMBER}   %{NOTEBOOK_BENCHMARK_NUMBER}
${NOTEBOOK_BENCHMARK_REPEAT}   %{NOTEBOOK_BENCHMARK_REPEAT}

${NOTEBOOK_SPAWN_WAIT_TIME}    20 minutes

${NOTEBOOK_URL}                %{NOTEBOOK_URL}
${NOTEBOOK_NAME}               notebook.ipynb
${NOTEBOOK_CLONE_WAIT_TIME}    3 minutes
${NOTEBOOK_EXEC_WAIT_TIME}     15 minutes

&{browser logging capability}    browser=ALL
&{capabilities}    browserName=chrome    version=${EMPTY}    platform=ANY    goog:loggingPrefs=${browser logging capability}

*** Test Cases ***

Open the Browser
  [Tags]  Setup

  Setup

Login to RHODS Dashboard
  [Tags]  Authenticate

  Login To RHODS Dashboard  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}


Go to RHODS Dashboard
  [Tags]  Dashboard

  Wait For Condition  return document.title == ${DASHBOARD_PRODUCT_NAME}  timeout=3 minutes
  Wait Until Page Contains  Launch application  timeout=60 seconds
  Capture Page Screenshot


Go to the Project page
  [Tags]  Dashboard

  Open Data Science Projects Home Page
  Capture Page Screenshot

  ${has_errors}  ${error}=  Run Keyword And Ignore Error  Project Should Be Listed  ${PROJECT_NAME}
  IF  '${has_errors}' != 'PASS'
    Create Data Science Project  ${PROJECT_NAME}  ${TEST_USER.USERNAME}'s project
  ELSE
    Open Data Science Project Details Page  ${PROJECT_NAME}
  END
  Capture Page Screenshot


Create and Start the Workbench
  [Tags]  Notebook Spawn

  Capture Page Screenshot
  ${workbench_exists}  ${error}=  Run Keyword And Ignore Error  Workbench Should Be Listed  ${WORKBENCH_NAME}
  IF  '${workbench_exists}' != 'PASS'
    Create Workbench  ${WORKBENCH_NAME}  ${PROJECT_NAME} workbench  ${PROJECT_NAME}  ${NOTEBOOK_IMAGE_NAME_DESCR}  ${NOTEBOOK_SIZE_NAME}  Ephemeral  ${NONE}  ${NONE}  ${NONE}  ${NONE}
    Wait Until Workbench Is Started  ${WORKBENCH_NAME}  timeout=${NOTEBOOK_SPAWN_WAIT_TIME}
  ELSE
    Workbench Status Should Be  ${WORKBENCH_NAME}  ${WORKBENCH_STATUS_STOPPED}
    Start Workbench  ${WORKBENCH_NAME}  ${NOTEBOOK_SPAWN_WAIT_TIME}
  END

  Capture Page Screenshot
  Workbench Status Should Be      workbench_title=${WORKBENCH_NAME}   status=${WORKBENCH_STATUS_RUNNING}
  ${workbench_launched}  ${error}=  Run Keyword And Ignore Error  Just Launch Workbench  ${WORKBENCH_NAME}
  IF  '${workbench_launched}' != 'PASS'
    Capture Page Screenshot  bug_5819_open_not_available.png
    Log     message=Workaround for RHODS-5819: reload the page    level=WARN
    Reload Page
    Wait Until Page Contains  Create workbench  timeout=60 seconds
    Just Launch Workbench  ${WORKBENCH_NAME}
  END

  ${app_is_ready} =    Run Keyword And Return Status    Page Should Not Contain  Application is not available
  IF  ${app_is_ready} != True
    Log     message=Workaround for RHODS-5912: reload the page    level=WARN
    Capture Page Screenshot  bug_5912_application_not_available.png
    oc_login  ${OCP_API_URL}  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}
    ${oa_logs}=  Oc Get Pod Logs  name=${WORKBENCH_NAME}-0  namespace=${PROJECT_NAME}  container=oauth-proxy
    ${jl_logs}=  Oc Get Pod Logs  name=${WORKBENCH_NAME}-0  namespace=${PROJECT_NAME}  container=${WORKBENCH_NAME}
    Create File  ${OUTPUTDIR}/pod_logs.txt  OAuth\n-----\n\n${oa_logs} \nJupyterLab\n----------\n\n${jl_logs}

    ${current_url}=   Get Location
    Create File  ${OUTPUTDIR}/bug_5912.url  ${current_url}

    ${current_html} =    SeleniumLibrary.Get Source
    Create File  ${OUTPUTDIR}/bug_5912.html  ${current_html}

    ${browser log entries}=    Get Browser Console Log Entries
    ${browser log entries str}=   Convert To String  ${browser log entries}
    Create File  ${OUTPUTDIR}/bug_5912_browser_log_entries.yaml  ${browser log entries str}

    Sleep  5s
    Reload Page
  END

Login to JupyterLab Page
  [Tags]  Notebook  Spawn

  Login To JupyterLab  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}  ${PROJECT_NAME}


Go to JupyterLab Page
  [Tags]  Notebook  Spawn

  Wait Until Page Contains Element  xpath:${JL_TABBAR_CONTENT_XPATH}  timeout=3 minutes
  Capture Page Screenshot


Load the Notebook
  [Tags]  Notebook  Run

   Load the Notebook


Run the Notebook
  [Tags]  Notebook  Run

  Run the Notebook


*** Keywords ***


Just Launch Workbench
    [Arguments]     ${workbench_title}

    Click Link       ${WORKBENCH_SECTION_XP}//tr[td[@data-label="Name"]/h4[div[text()="${workbench_title}"]]]//a[text()="Open"]
    Switch Window   NEW
