*** Settings ***
Resource            tests/Resources/RHOSi.resource

*** Keywords ***

Setup
  Set Library Search Order  SeleniumLibrary
  Protect Sensitive Variables In Keywords
  Open Browser  browser=${BROWSER.NAME}  options=${BROWSER.OPTIONS}

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

Load the Notebook
  Maybe Close Popup
  ${is_launcher_selected} =  Run Keyword And Return Status  JupyterLab Launcher Tab Is Selected
  Run Keyword If  not ${is_launcher_selected}  Open JupyterLab Launcher
  Capture Page Screenshot
  Launch a new JupyterLab Document
  Maybe Close Popup
  Close Other JupyterLab Tabs

  ${rest}  ${notebook_name}=  Split String From Right  ${NOTEBOOK_URL}  /  1
  # shell command (with ! prefix) errors are ignored by JupyterLab
  Add and Run JupyterLab Code Cell in Active Notebook  !time curl -Ssf "${NOTEBOOK_URL}" -o "${notebook_name}"
  Add and Run JupyterLab Code Cell in Active Notebook  !time curl -Ssf "${NOTEBOOK_URL}/../${NOTEBOOK_BENCHMARK_NAME}" -O
  Wait Until JupyterLab Code Cell Is Not Active  timeout=${NOTEBOOK_CLONE_WAIT_TIME}
  My Run Cell And Check For Errors  import pathlib; pathlib.Path("${notebook_name}").stat()
  My Run Cell And Check For Errors  import pathlib; pathlib.Path("${NOTEBOOK_BENCHMARK_NAME}").stat()
  Capture Page Screenshot

  Open With JupyterLab Menu  File  Open from Path…
  Input Text  xpath=//input[@placeholder="/path/relative/to/jlab/root"]  ${notebook_name}
  Click Element  xpath://div[.="Open"]
  Wait Until ${notebook_name} JupyterLab Tab Is Selected
  Close Other JupyterLab Tabs
  Open With JupyterLab Menu  Edit  Clear All Outputs
  Capture Page Screenshot

Run the Notebook

  Run Cell And Check For Errors  import datetime;print(f"{datetime.datetime.now()} Configuring ...")
  Run Cell And Check For Errors  import os;os.environ["BENCHMARK_NAME"]="${NOTEBOOK_BENCHMARK_NAME}";os.environ["BENCHMARK_REPEAT"]="${NOTEBOOK_BENCHMARK_REPEAT}"; os.environ["BENCHMARK_NUMBER"]="${NOTEBOOK_BENCHMARK_NUMBER}";
  Open With JupyterLab Menu  Run  Run All Cells
  Capture Page Screenshot

  Wait Until JupyterLab Code Cell Is Not Active  timeout=${NOTEBOOK_EXEC_WAIT_TIME}
  Capture Page Screenshot
  ${has_errors}  ${error}=  Run Keyword And Ignore Error  Get JupyterLab Code Cell Error Text

  IF  '${has_errors}' == 'PASS'
      Log  ${error}
      Fail  "Error detected during the execution of the notebook:\n${error}"
  END

  My Run Cell And Check For Errors  print(f"The benchmark ran for {sum(measures):.2f} seconds")

  ${measures} =  Run Cell And Get Output  print(results)
  Create File  ${OUTPUTDIR}/benchmark_measures.json  ${measures}

  Capture Page Screenshot

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

My Run Cell And Check For Errors
  [Arguments]  ${input}  ${timeout}=120 seconds

  Add and Run JupyterLab Code Cell in Active Notebook  ${input}
  Wait Until JupyterLab Code Cell Is Not Active  ${timeout}
  ${output} =  Get Text  (//div[contains(@class,"jp-OutputArea-output")])[last()]
  Should Not Match  ${output}  ERROR*
