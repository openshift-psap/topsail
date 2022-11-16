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

*** Variables ***

${DASHBOARD_PRODUCT_NAME}      "%{DASHBOARD_PRODUCT_NAME}"

${NOTEBOOK_IMAGE_NAME}         %{NOTEBOOK_IMAGE_NAME}

${NOTEBOOK_BENCHMARK_NAME}     %{NOTEBOOK_BENCHMARK_NAME}
${NOTEBOOK_BENCHMARK_NUMBER}   %{NOTEBOOK_BENCHMARK_NUMBER}
${NOTEBOOK_BENCHMARK_REPEAT}   %{NOTEBOOK_BENCHMARK_REPEAT}

${NOTEBOOK_IMAGE_SIZE}         %{NOTEBOOK_SIZE_NAME}
${NOTEBOOK_SPAWN_WAIT_TIME}    20 minutes

${NOTEBOOK_URL}                %{NOTEBOOK_URL}
${NOTEBOOK_NAME}               notebook.ipynb
${NOTEBOOK_CLONE_WAIT_TIME}    3 minutes
${NOTEBOOK_EXEC_WAIT_TIME}     15 minutes

&{browser logging capability}    browser=ALL
&{capabilities}    browserName=chrome    version=${EMPTY}    platform=ANY    goog:loggingPrefs=${browser logging capability}

*** Keywords ***

Setup
  Set Library Search Order  SeleniumLibrary
  Initialize Global Variables
  Open Browser  ${ODH_DASHBOARD_URL}  browser=${BROWSER.NAME}  options=${BROWSER.OPTIONS}  desired_capabilities=${capabilities}

Tear Down
  ${browser log entries}=    Get Browser Console Log Entries
  Log    ${browser log entries}
  ${browser log entries str}=   Convert To String  ${browser log entries}
  Create File  ${OUTPUTDIR}/browser_log_entries.yaml  ${browser log entries str}

  Capture Page Screenshot  final_screenshot.png

  ${final_url}=   Get Location
  Create File  ${OUTPUTDIR}/final.url  ${final_url}

  ${final_html} =    Get Source
  Create File  ${OUTPUTDIR}/final.html  ${final_url}

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


Go to Jupyter Page
  [Tags]  Dashboard

  Launch Jupyter From RHODS Dashboard Link
  Wait Until Page Contains  Start a notebook server  timeout=60 seconds
  Wait Until Page Contains  Start server  timeout=60 seconds
  Capture Page Screenshot

  Select Notebook Image  ${NOTEBOOK_IMAGE_NAME}
  Select Container Size  ${NOTEBOOK_IMAGE_SIZE}

  Capture Page Screenshot


Wait for the Notebook Spawn
  [Tags]  Notebook  Spawn

  Trigger Notebook Spawn
  Click Element  xpath://span[@class="pf-c-expandable-section__toggle-text"]
  Capture Page Screenshot

  Wait Notebook Spawn  ${NOTEBOOK_SPAWN_WAIT_TIME}
  Capture Page Screenshot


Login to JupyterLab Page
  [Tags]  Notebook  Spawn

  Login To JupyterLab  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}


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
   [Arguments]  ${ocp_user_name}  ${ocp_user_pw}  ${ocp_user_auth_type}

   ${oauth_prompt_visible} =  Is OpenShift OAuth Login Prompt Visible
   Run Keyword If  ${oauth_prompt_visible}  Click Button  Log in with OpenShift
   ${login-required} =  Is OpenShift Login Visible
   Run Keyword If  ${login-required}  Login To Openshift  ${ocp_user_name}  ${ocp_user_pw}  ${ocp_user_auth_type}
   ${authorize_service_account} =  Is jupyter-nb-${TEST_USER.USERNAME} Service Account Authorization Required
   # correct name not required/not working, not sure why
   Run Keyword If  ${authorize_service_account}  Authorize rhods-dashboard service account


Trigger Notebook Spawn
  [Arguments]  ${modal_timeout}=60 seconds

  ${rhods_17_or_above}=  Is RHODS Version Greater Or Equal Than  1.17.0
  IF  ${rhods_17_or_above} == True
      ${notebook_browser_tab_preference}=  Set Variable  //input[@id="checkbox-notebook-browser-tab-preference"]
      ${new_tab_checked}  Get Element Attribute  ${notebook_browser_tab_preference}  checked
      Run Keyword If  "${new_tab_checked}" == "${None}"  Click Element  xpath:${notebook_browser_tab_preference}
  END
  Click Button  Start server
  Wait Until Page Contains  Starting server  ${modal_timeout}
  Wait Until Element Is Visible  xpath://div[@role="progressbar"]


Wait Notebook Spawn
  [Arguments]  ${spawner_timeout}=600 seconds

  Wait Until Page Does Not Contain Element  xpath://div[@role="progressbar"]  ${spawner_timeout}


Run Cell And Check For Errors
  [Arguments]  ${input}  ${timeout}=120 seconds

  Add and Run JupyterLab Code Cell in Active Notebook  ${input}
  Wait Until JupyterLab Code Cell Is Not Active  ${timeout}
  ${output} =  Get Text  (//div[contains(@class,"jp-OutputArea-output")])[last()]
  Should Not Match  ${output}  ERROR*
