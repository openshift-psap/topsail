*** Settings ***
Resource            tests/Resources/ODS.robot
Resource            tests/Resources/Common.robot
Resource            tests/Resources/Page/ODH/ODHDashboard/ODHDataScienceProject/Workbenches.resource
Resource            tests/Resources/Page/ODH/ODHDashboard/ODHDataScienceProject/Projects.resource

Library             DateTime
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

${TEST_ONLY_CREATE_NOTEBOOKS}   %{TEST_ONLY_CREATE_NOTEBOOKS}

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

  Go To  ${ODH_DASHBOARD_URL}
  Login To RHODS Dashboard  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}


Go to RHODS Dashboard
  [Tags]  Dashboard

  Wait For Condition  return document.title == ${DASHBOARD_PRODUCT_NAME}  timeout=3 minutes
  Wait Until Page Contains  Launch application  timeout=3 minutes
  Capture Page Screenshot


Go to the Project page
  [Tags]  Dashboard

  Open Data Science Projects Home Page
  Wait Until Page Contains No Spinner

  Capture Page Screenshot

  ${has_errors}  ${error}=  Run Keyword And Ignore Error  Project Should Be Listed  ${PROJECT_NAME}
  IF  '${has_errors}' != 'PASS'
    Create Data Science Project  ${PROJECT_NAME}  ${TEST_USER.USERNAME}'s project
  ELSE
    Open Data Science Project Details Page  ${PROJECT_NAME}
  END
  Wait Until Page Contains No Spinner
  Capture Page Screenshot


Create and Start the Workbench
  [Tags]  Notebook  Spawn

  ${workbench_exists}  ${error}=  Run Keyword And Ignore Error  Workbench Is Listed  ${WORKBENCH_NAME}
  IF  '${workbench_exists}' == 'FAIL'
    Create Workbench  ${WORKBENCH_NAME}  ${PROJECT_NAME} workbench  ${PROJECT_NAME}  ${NOTEBOOK_IMAGE_NAME_DESCR}  ${NOTEBOOK_SIZE_NAME}  Persistent  ${FALSE}  ${WORKBENCH_NAME}  ${WORKBENCH_NAME}  pv_size=5
    Capture Page Screenshot

    IF  '${TEST_ONLY_CREATE_NOTEBOOKS}' == 'True'
      Wait Until Workbench Is Starting  ${WORKBENCH_NAME}  timeout=30 seconds
      Stop Starting Workbench  ${WORKBENCH_NAME}
      Capture Page Screenshot
      Log     message=Stopped after creating the workbench    level=WARN
      Skip  # skip is the only way I found to return without failing the test
    END

    Wait Until Workbench Is Started  ${WORKBENCH_NAME}  timeout=${NOTEBOOK_SPAWN_WAIT_TIME}
  ELSE
    Workbench Status Should Be  ${WORKBENCH_NAME}  ${WORKBENCH_STATUS_STOPPED}
    Capture Page Screenshot
    IF  '${TEST_ONLY_CREATE_NOTEBOOKS}' == 'True'
      Log     message=Stopped after checking that the workbench existed    level=WARN
      Skip  # skip is the only way to return without failing the test
    END
    Start Workbench  ${WORKBENCH_NAME}  ${NOTEBOOK_SPAWN_WAIT_TIME}
  END

  Capture Page Screenshot
  Workbench Status Should Be      workbench_title=${WORKBENCH_NAME}   status=${WORKBENCH_STATUS_RUNNING}
  ${workbench_launched}  ${error}=  Run Keyword And Ignore Error  Just Launch Workbench  ${WORKBENCH_NAME}

  ${app_is_ready} =    Run Keyword And Return Status    Page Should Not Contain  Application is not available
  IF  ${app_is_ready} != True
    Log     message=Workaround for RHODS-5912: reload the page    level=WARN
    Capture Page Screenshot  bug_5912_application_not_available.png
    oc_login  ${OCP_API_URL}  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}
    ${oa_logs}=  Oc Get Pod Logs  name=${WORKBENCH_NAME}-0  namespace=${PROJECT_NAME}  container=oauth-proxy
    ${jl_logs}=  Oc Get Pod Logs  name=${WORKBENCH_NAME}-0  namespace=${PROJECT_NAME}  container=${WORKBENCH_NAME}
    Create File  ${OUTPUTDIR}/pod_logs.txt  OAuth\n-----\n\n${oa_logs} \nJupyterLab\n----------\n\n${jl_logs}

    ${endpoints}=  Oc Get  kind=Endpoints  namespace=${PROJECT_NAME}
    ${route}=  Oc Get  kind=Route  name=${WORKBENCH_NAME}  namespace=${PROJECT_NAME}  api_version=route.openshift.io/v1
    ${endpoints_str}=  Convert to String  ${endpoints}
    Create File  ${OUTPUTDIR}/bug_5912.endpoints  ${endpoints_str}
    ${route_str}=  Convert to String  ${route}
    Create File  ${OUTPUTDIR}/bug_5912.route  ${route_str}

    ${current_url}=   Get Location
    Create File  ${OUTPUTDIR}/bug_5912.url  ${current_url}

    ${current_html} =    SeleniumLibrary.Get Source
    Create File  ${OUTPUTDIR}/bug_5912.html  ${current_html}

    ${browser log entries}=    Get Browser Console Log Entries
    ${browser log entries str}=   Convert To String  ${browser log entries}
    Create File  ${OUTPUTDIR}/bug_5912_browser_log_entries.yaml  ${browser log entries str}

    Sleep  3s
    Reload Page
    Page Should Not Contain  Application is not available
  END

Login to JupyterLab Page
  [Tags]  Notebook  JupyterLab  Login

  Login To JupyterLab  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}  ${PROJECT_NAME}


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


Just Launch Workbench
    [Arguments]     ${workbench_title}

    Click Link       ${WORKBENCH_SECTION_XP}//tr[td[@data-label="Name"]/h3[div[starts-with(text(), "${workbench_title}")]]]//a[text()="Open"]
    Switch Window   NEW

Wait Until Page Contains No Spinner
    [Arguments]     ${timeout}=30 seconds
    Wait Until Page Does Not Contain Element   //*[contains(@class, 'pf-c-spinner')]  timeout=${timeout}

Wait Until Workbench Is Starting
    [Documentation]    Waits until workbench status is "Starting..." in the DS Project details page
    [Arguments]     ${workbench_title}      ${timeout}=30s    ${status}=${WORKBENCH_STATUS_STARTING}

    Wait Until Page Contains Element
    ...        ${WORKBENCH_SECTION_XP}//tr[td[@data-label="Name"]/h3[div[starts-with(text(), "${workbench_title}")]]]/td[@data-label="Status"]//p[text()="${status}"]    timeout=${timeout}

Stop Starting Workbench
    [Documentation]    Stops a starting workbench from DS Project details page
    [Arguments]     ${workbench_title}    ${press_cancel}=${FALSE}
    ${is_stopped}=      Run Keyword And Return Status   Workbench Status Should Be
    ...    workbench_title=${workbench_title}   status=${WORKBENCH_STATUS_STOPPED}
    IF    ${is_stopped} == ${False}
        Click Element       ${WORKBENCH_SECTION_XP}//tr[td[@data-label="Name"]/h3[div[starts-with(text(), "${workbench_title}")]]]/td[@data-label="Status"]//span[@class="pf-c-switch__toggle"]
        Wait Until Generic Modal Appears
        Page Should Contain    Are you sure you want to stop the workbench? Any changes without saving will be erased.
        Click Button    ${WORKBENCH_STOP_BTN_XP}
    ELSE
        Fail   msg=Cannot stop workbench ${workbench_title} because it is always stopped..
    END

Workbench is Listed
    [Documentation]    Checks a workbench is listed in the DS Project details page
    [Arguments]     ${workbench_title}
    Run keyword And Continue On Failure
    ...    Page Should Contain Element
    ...        ${WORKBENCH_SECTION_XP}//td[@data-label="Name"]/h3[div[starts-with(text(), "${workbench_title}")]]
