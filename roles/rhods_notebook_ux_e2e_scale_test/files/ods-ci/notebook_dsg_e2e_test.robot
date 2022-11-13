*** Settings ***
Resource            tests/Resources/ODS.robot
Resource            tests/Resources/Common.robot
Resource            tests/Resources/Page/ODH/ODHDashboard/ODHDataScienceProject/Workbenches.resource
Resource            tests/Resources/Page/ODH/ODHDashboard/ODHDataScienceProject/Projects.resource

Library             JupyterLibrary
Library             libs/Helpers.py
Library             SeleniumLibrary
#Library             DebugLibrary  # then use the 'Debug' keyword to set a breakpoint

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

${NOTEBOOK_SPAWN_WAIT_TIME}    2 minutes

${NOTEBOOK_URL}                %{NOTEBOOK_URL}
${NOTEBOOK_NAME}               notebook.ipynb
${NOTEBOOK_CLONE_WAIT_TIME}    3 minutes
${NOTEBOOK_EXEC_WAIT_TIME}     15 minutes

&{browser logging capability}    browser=ALL
&{capabilities}    browserName=chrome    version=${EMPTY}    platform=ANY    goog:loggingPrefs=${browser logging capability}

*** Keywords ***

Setup
  Set Library Search Order  SeleniumLibrary
  #Initialize Global Variables
  Open Browser  ${ODH_DASHBOARD_URL}  browser=${BROWSER.NAME}  options=${BROWSER.OPTIONS}  desired_capabilities=${capabilities}

Tear Down
  ${browser log entries}=    Get Browser Console Log Entries
  Log    ${browser log entries}
  ${browser log entries str}=   Convert To String  ${browser log entries}
  Create File  ${OUTPUTDIR}/browser_log_entries.yaml  ${browser log entries str}

  Capture Page Screenshot  final_screenshot.png

  ${final_url}=   Get Location
  Create File  ${OUTPUTDIR}/final.url  ${final_url}

  ${final_html} =    SeleniumLibrary.Get Source
  Create File  ${OUTPUTDIR}/final.html  ${final_html}

  Close Browser

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
    Start Workbench  ${WORKBENCH_NAME}
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


Login to JupyterLab Page
  [Tags]  Notebook  Spawn

  Login To JupyterLab  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}  ${PROJECT_NAME}


Go to JupyterLab Page
  [Tags]  Notebook  Spawn

  Wait Until Page Contains Element  xpath:${JL_TABBAR_CONTENT_XPATH}  timeout=3 minutes
  Capture Page Screenshot


Load the Notebook
  [Tags]  Notebook  Run

  Maybe Close Popup
  ${is_launcher_selected} =  Run Keyword And Return Status  JupyterLab Launcher Tab Is Selected
  Run Keyword If  not ${is_launcher_selected}  Open JupyterLab Launcher
  Capture Page Screenshot
  Launch a new JupyterLab Document
  Maybe Close Popup
  Close Other JupyterLab Tabs
  # shell command (with ! prefix) errors are ignored by JupyterLab
  Add and Run JupyterLab Code Cell in Active Notebook  !time curl -Ssf "${NOTEBOOK_URL}" -o "${NOTEBOOK_NAME}"
  Add and Run JupyterLab Code Cell in Active Notebook  !time curl -Ssf "${NOTEBOOK_URL}/../${NOTEBOOK_BENCHMARK_NAME}" -O
  Wait Until JupyterLab Code Cell Is Not Active  timeout=${NOTEBOOK_CLONE_WAIT_TIME}
  Run Cell And Check For Errors  import pathlib; pathlib.Path("${NOTEBOOK_NAME}").stat()
  Run Cell And Check For Errors  import pathlib; pathlib.Path("${NOTEBOOK_BENCHMARK_NAME}").stat()
  Capture Page Screenshot

  Open With JupyterLab Menu  File  Open from Path…
  Input Text  xpath=//input[@placeholder="/path/relative/to/jlab/root"]  ${NOTEBOOK_NAME}
  Click Element  xpath://div[.="Open"]
  Wait Until ${NOTEBOOK_NAME} JupyterLab Tab Is Selected
  Close Other JupyterLab Tabs
  Capture Page Screenshot


Run the Notebook
  [Tags]  Notebook  Run

  Open With JupyterLab Menu  Run  Run All Cells
  Capture Page Screenshot

  Wait Until JupyterLab Code Cell Is Not Active  timeout=${NOTEBOOK_EXEC_WAIT_TIME}
  Capture Page Screenshot
  ${has_errors}  ${error}=  Run Keyword And Ignore Error  Get JupyterLab Code Cell Error Text

  IF  '${has_errors}' == 'PASS'
      Log  ${error}
      Fail  "Error detected during the execution of the notebook:\n${error}"
  END

  Run Cell And Check For Errors  print(f"{datetime.datetime.now()} Running ...")
  Run Cell And Check For Errors  REPEAT=${NOTEBOOK_BENCHMARK_REPEAT}; NUMBER=${NOTEBOOK_BENCHMARK_NUMBER}
  Run Cell And Check For Errors  measures = run_benchmark(repeat=REPEAT, number=NUMBER)  timeout=${NOTEBOOK_EXEC_WAIT_TIME}
  Run Cell And Check For Errors  print(f"{datetime.datetime.now()} Done ...")
  Run Cell And Check For Errors  print(f"The benchmark ran for {sum(measures):.2f} seconds")
  ${measures} =  Run Cell And Get Output  import json; print(json.dumps(dict(benchmark="${NOTEBOOK_BENCHMARK_NAME}", repeat=REPEAT, number=NUMBER, measures=measures)))
  Create File  ${OUTPUTDIR}/benchmark_measures.json  ${measures}

  Capture Page Screenshot


*** Keywords ***

Get Browser Console Log Entries
    ${selenium}=    Get Library Instance    SeleniumLibrary
    ${webdriver}=    Set Variable     ${selenium._drivers.active_drivers}[0]
    ${log entries}=    Evaluate    $webdriver.get_log('browser')
    [Return]    ${log entries}

Login To JupyterLab
   [Arguments]  ${ocp_user_name}  ${ocp_user_pw}  ${ocp_user_auth_type}  ${sa_name}=jupyter-nb-${TEST_USER.USERNAME}

   ${oauth_prompt_visible} =  Is OpenShift OAuth Login Prompt Visible
   Run Keyword If  ${oauth_prompt_visible}  Click Button  Log in with OpenShift
   ${login-required} =  Is OpenShift Login Visible
   Run Keyword If  ${login-required}  Login To Openshift  ${ocp_user_name}  ${ocp_user_pw}  ${ocp_user_auth_type}
   ${authorize_service_account} =  Is ${sa_name} Service Account Authorization Required
   # correct name not required/not working, not sure why
   Run Keyword If  ${authorize_service_account}  Authorize rhods-dashboard service account


Run Cell And Check For Errors
  [Arguments]  ${input}  ${timeout}=120 seconds

  Add and Run JupyterLab Code Cell in Active Notebook  ${input}
  Wait Until JupyterLab Code Cell Is Not Active  ${timeout}
  ${output} =  Get Text  (//div[contains(@class,"jp-OutputArea-output")])[last()]
  Should Not Match  ${output}  ERROR*

Just Launch Workbench
    [Arguments]     ${workbench_title}

    Click Link       ${WORKBENCH_SECTION_XP}//tr[td[@data-label="Name"]/h4[div[text()="${workbench_title}"]]]/td/a[text()="Open"]
    Switch Window   NEW
