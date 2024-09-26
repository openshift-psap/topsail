*** Settings ***
Resource            tests/Resources/ODS.robot
Resource            tests/Resources/Common.robot
Resource            tests/Resources/Page/ODH/ODHDashboard/ODHDataScienceProject/Workbenches.resource
Resource            tests/Resources/Page/ODH/ODHDashboard/ODHDataScienceProject/Projects.resource
Resource            tests/Resources/Page/ODH/ODHDashboard/ODHDataScienceProject/DataConnections.resource
Resource            tests/Resources/Page/ODH/ODHDashboard/ODHDataScienceProject/Pipelines.resource
Resource            tests/Resources/Page/ODH/JupyterHub/Elyra.resource

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
${ACCESS_KEY}                  %{S3_ACCESS_KEY}
${HOST_BASE}                   %{S3_HOSTNAME}
${HOST_BUCKET}                 %{S3_BUCKET_NAME}
${DC_NAME}                     elyra-s3
${IMAGE}                       Standard Data Science
${PV_NAME}                     ${TEST_USER.USERNAME}_pvc
${PV_DESCRIPTION}              ${TEST_USER.USERNAME} is a PV created to test Elyra in workbenches
${PV_SIZE}                     2
${PIPELINE_IMPORT_BUTTON}      xpath=//button[@id='import-pipeline-button']
${PIPELINES_SERVER_BTN_XP}     xpath=//*[@data-testid="create-pipeline-button"]
${SVG_CANVAS}                  //*[name()="svg" and @class="svg-area"]
${SVG_INTERACTABLE}            /*[name()="g" and @class="d3-canvas-group"]
${SVG_PIPELINE_NODES}          /*[name()="g" and @class="d3-nodes-links-group"]
${SVG_SINGLE_NODE}             /*[name()="g" and contains(@class, "d3-draggable")]
${EXPECTED_COLOR}              rgb(0, 102, 204)
${EXPERIMENT_NAME}             standard data science pipeline
${NOTEBOOK_SPAWN_WAIT_TIME}    20 minutes
${WORKBENCH_NAME}              ${TEST_USER.USERNAME}
${ODH_DASHBOARD_DO_NOT_WAIT_FOR_SPINNER_PAGE}  ${true}

*** Test Cases ***

Open the Browser
  [Tags]  Setup

  Setup

Login to RHODS Dashboard
  [Tags]  Authenticate

  Go To  ${ODH_DASHBOARD_URL}
  Login To RHODS Dashboard  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}  ${TEST_USER.AUTH_TYPE}
  Capture Page Screenshot

Go to RHODS Dashboard
  [Tags]  Dashboard

  Wait For Condition  return document.title == ${DASHBOARD_PRODUCT_NAME}  timeout=3 minutes
  Wait Until Page Contains  Data Science Projects  timeout=3 minutes
  Capture Page Screenshot

Go to the Project page
  [Tags]  Dashboard

  Open Data Science Projects Home Page
  Wait Until Page Contains No Spinner

  Capture Page Screenshot

  ${has_errors}  ${error}=  Run Keyword And Ignore Error  Project Should Be Listed  ${PROJECT_NAME}
  IF  '${has_errors}' != 'PASS'
    Create Data Science Project Elyra  ${PROJECT_NAME}  ${TEST_USER.USERNAME}'s project
  ELSE
    Open Data Science Project Details Page  ${PROJECT_NAME}
  END
  Wait Until Page Contains No Spinner
  Capture Page Screenshot
  
# Create S3 Data Connection Creation  
#   [Tags]  Dashboard

#   ${data_connection_exists}  ${error}=  Run Keyword and Ignore Error  Data Connection Should Not Be Listed  ${DC_NAME}
#   IF  '${data_connection_exists}' != 'PASS'
#     Create S3 Data Connection   project_title=${PROJECT_NAME}   dc_name=${DC_NAME}    aws_access_key=${ACCESS_KEY}    aws_secret_access=${TEST_USER.PASSWORD}   aws_bucket_name=${HOST_BUCKET}  aws_s3_endpoint=${HOST_BASE}
#   ELSE
#     Recreate S3 Data Connection   project_title=${PROJECT_NAME}   dc_name=${DC_NAME}    aws_access_key=${ACCESS_KEY}    aws_secret_access=${TEST_USER.PASSWORD}   aws_bucket_name=${HOST_BUCKET}  aws_s3_endpoint=${HOST_BASE}
#   END
#   Capture Page Screenshot

# Create Pipeline Server To s3
#   [Tags]  Dashboard
#   oc_login  ${OCP_API_URL}  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}
#   Pipelines.Create Pipeline Server    dc_name=${DC_NAME}    project_title=${PROJECT_NAME}
#   Verify There Is No "Error Displaying Pipelines" After Creating Pipeline Server
#   Verify That There Are No Sample Pipelines After Creating Pipeline Server
#   Wait Until Pipeline Server Is Deployed Elyra    project_title=${PROJECT_NAME}
#   Capture Page Screenshot

# Create and Start the Workbench
#   [Tags]  Dashboard

#   ${workbench_exists}  ${error}=  Run Keyword And Ignore Error  Workbench Is Listed  ${WORKBENCH_NAME}
#   IF  '${workbench_exists}' == 'FAIL'  
#     Create Workbench    workbench_title=${WORKBENCH_NAME}    workbench_description=Elyra test    prj_title=${PROJECT_NAME}   image_name=${IMAGE}   deployment_size=Tiny    storage=Persistent    pv_existent=${FALSE}    pv_name=${PV_NAME}   pv_description=${PV_DESCRIPTION}    pv_size=${PV_SIZE}    
#   END
#   Start Workbench     workbench_title=${WORKBENCH_NAME}    timeout=300s
#   Capture Page Screenshot
#   Workbench Status Should Be      workbench_title=${WORKBENCH_NAME}   status=${WORKBENCH_STATUS_RUNNING}
#   ${workbench_launched}  ${error}=  Run Keyword And Ignore Error  Just Launch Workbench  ${WORKBENCH_NAME}

#   ${app_is_ready} =    Run Keyword And Return Status    Page Should Not Contain  Application is not available
#   IF  ${app_is_ready} != True
#     Log     message=Workaround for RHODS-5912: reload the page    level=WARN
#     Capture Page Screenshot  bug_5912_application_not_available.png
#     oc_login  ${OCP_API_URL}  ${TEST_USER.USERNAME}  ${TEST_USER.PASSWORD}
#     ${oa_logs}=  Oc Get Pod Logs  name=${WORKBENCH_NAME}-0  namespace=${PROJECT_NAME}  container=oauth-proxy
#     ${jl_logs}=  Oc Get Pod Logs  name=${WORKBENCH_NAME}-0  namespace=${PROJECT_NAME}  container=${WORKBENCH_NAME}
#     Create File  ${OUTPUTDIR}/pod_logs.txt  OAuth\n-----\n\n${oa_logs} \nJupyterLab\n----------\n\n${jl_logs}

#     ${endpoints}=  Oc Get  kind=Endpoints  namespace=${PROJECT_NAME}
#     ${route}=  Oc Get  kind=Route  name=${WORKBENCH_NAME}  namespace=${PROJECT_NAME}  api_version=route.openshift.io/v1
#     ${endpoints_str}=  Convert to String  ${endpoints}
#     Create File  ${OUTPUTDIR}/bug_5912.endpoints  ${endpoints_str}
#     ${route_str}=  Convert to String  ${route}
#     Create File  ${OUTPUTDIR}/bug_5912.route  ${route_str}

#     ${current_url}=   Get Location
#     Create File  ${OUTPUTDIR}/bug_5912.url  ${current_url}

#     ${current_html} =    SeleniumLibrary.Get Source
#     Create File  ${OUTPUTDIR}/bug_5912.html  ${current_html}

#     ${browser log entries}=    Get Browser Console Log Entries
#     ${browser log entries str}=   Convert To String  ${browser log entries}
#     Create File  ${OUTPUTDIR}/bug_5912_browser_log_entries.yaml  ${browser log entries str}

#     Sleep  30s
#     Reload Page
#     Page Should Not Contain  Application is not available
#   END   
#   Access To Workbench    username=${TEST_USER.USERNAME}    password=${TEST_USER.PASSWORD}
#         ...    auth_type=${TEST_USER.AUTH_TYPE}
#   Capture Page Screenshot
#   Navigate Home (Root folder) In JupyterLab Sidebar File Browser
#   Clone Git Repository And Open    https://github.com/redhat-rhods-qe/ods-ci-notebooks-main
#   ...    ods-ci-notebooks-main/notebooks/500__jupyterhub/pipelines/v2/elyra/run-pipelines-on-data-science-pipelines/hello-generic-world.pipeline  # robocop: disable
#   Verify Hello World Pipeline Elements
#   Set Runtime Image In All Nodes    runtime_image=Datascience with Python 3.9 (UBI9)
#   Run Pipeline    pipeline_name=${IMAGE} Pipeline
#   Wait Until Page Contains Element    xpath=//a[.="Run Details."]
#   Capture Page Screenshot

# Check of Pipeline Runs
#   [Tags]  Dashboard

#   ${pipeline_run_name} =    Get Pipeline Run Name
#   Switch To Pipeline Execution Page
#   Is Data Science Project Details Page Open   ${PROJECT_NAME}
#   Verify Elyra Pipeline Run    pipeline_run_name=${pipeline_run_name}    timeout=30m    experiment_name=${EXPERIMENT_NAME}

*** Keywords ***

Just Launch Workbench
    [Arguments]     ${workbench_title}

    Click Link      ${WORKBENCH_SECTION_XP}//tr[td[@data-label="Name"]/*[div[text()="${workbench_title}"]]]/td//a[text()="Open"]
    Switch Window   NEW

Wait Until Page Contains No Spinner
    [Arguments]     ${timeout}=1m
    Wait Until Page Does Not Contain Element   //*[contains(@class, 'pf-c-spinner')]  timeout=${timeout}

Wait Until Workbench Is Starting
    [Documentation]    Waits until workbench status is "Starting..." in the DS Project details page
    [Arguments]     ${workbench_title}      ${timeout}=30s    ${status}=${WORKBENCH_STATUS_STARTING}

    Wait Until Page Contains Element
    ...        ${WORKBENCH_SECTION_XP}//tr[td[@data-label="Name"]/*[div[starts-with(text(), "${workbench_title}")]]]/td[@data-label="Status"]//p[text()="${status}"]    timeout=${timeout}

Stop Starting Workbench
    [Documentation]    Stops a starting workbench from DS Project details page
    [Arguments]     ${workbench_title}    ${press_cancel}=${FALSE}
    ${is_stopped}=      Run Keyword And Return Status   Workbench Status Should Be
    ...    workbench_title=${workbench_title}   status=${WORKBENCH_STATUS_STOPPED}
    IF    ${is_stopped} == ${False}
        Click Element       ${WORKBENCH_SECTION_XP}//tr[td[@data-label="Name"]/*[div[starts-with(text(), "${workbench_title}")]]]/td[@data-label="Status"]//span[@class="pf-v5-c-switch__toggle"]
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
    ...        ${WORKBENCH_SECTION_XP}//td[@data-label="Name"]/*[div[starts-with(text(), "${workbench_title}")]]

Wait Until Pipeline Server Deployed 
    [Documentation]    waits untill the pipeline server deployed and have the button import pipeline button 
    Wait Until Page Does Not Contain Element   //*[contains(@class, 'pf-c-spinner')]  timeout=3 minutes
        

Verify Hello World Pipeline Elements
    [Documentation]    Verifies that the example pipeline is displayed correctly by Elyra
    Wait Until Page Contains Element    xpath=${SVG_CANVAS}     timeout=2m
    Maybe Migrate Pipeline
    Page Should Contain Element    xpath=${SVG_CANVAS}${SVG_INTERACTABLE}${SVG_PIPELINE_NODES}${SVG_SINGLE_NODE}//span[.="Load weather data"]  # robocop: disable
    Page Should Contain Element    xpath=${SVG_CANVAS}${SVG_INTERACTABLE}${SVG_PIPELINE_NODES}${SVG_SINGLE_NODE}//span[.="Part 1 - Data Cleaning.ipynb"]  # robocop: disable
    Page Should Contain Element    xpath=${SVG_CANVAS}${SVG_INTERACTABLE}${SVG_PIPELINE_NODES}${SVG_SINGLE_NODE}//span[.="Part 2 - Data Analysis.ipynb"]  # robocop: disable
    Page Should Contain Element    xpath=${SVG_CANVAS}${SVG_INTERACTABLE}${SVG_PIPELINE_NODES}${SVG_SINGLE_NODE}//span[.="Part 3 - Time Series Forecasting.ipynb"]  # robocop: disable

Launch And Access Workbench Elyra Pipelines 
    [Documentation]    Launches a workbench from DS Project details page
    [Arguments]     ${workbench_title}    ${username}=${TEST_USER.USERNAME}
    ...    ${password}=${TEST_USER.PASSWORD}  ${auth_type}=${TEST_USER.AUTH_TYPE}
    ${is_started}=      Run Keyword And Return Status   Workbench Status Should Be
    ...    workbench_title=${workbench_title}   status=${WORKBENCH_STATUS_RUNNING}
    IF    ${is_started} == ${TRUE}
        Open Workbench    workbench_title=${workbench_title}
        Access To Workbench    username=${username}    password=${password}
        ...    auth_type=${auth_type}
    ELSE
        Fail   msg=Cannot Launch And Access Workbench ${workbench_title} because it is not running...
    END

Verify Elyra Pipeline Run 
    [Documentation]    Verifys Elyra Pipeline runs are sucessfull
    [Arguments]    ${pipeline_run_name}    ${timeout}=10m   ${experiment_name}=Default
    # Open Pipeline Elyra Pipeline Run    ${pipeline_run_name}    ${experiment_name}
    Wait Until Page Contains Element    //span[@class='pf-v5-c-label__text' and text()='Succeeded']    timeout=${timeout}
    Capture Page Screenshot  

Wait Until Pipeline Server Is Deployed Elyra
    [Documentation]    Waits until all the expected pods of the pipeline server
    ...                are running
    [Arguments]    ${project_title}
    Wait Until Keyword Succeeds    10 times    10s
    ...    Verify Pipeline Server Deployments Elyra    project_title=${project_title}

Verify Pipeline Server Deployments Elyra    # robocop: disable
    [Documentation]    Verifies the correct deployment of DS Pipelines in the rhods namespace
    [Arguments]    ${project_title}

    ${namespace}=    Get Openshift Namespace From Data Science Project
    ...    project_title=${project_title}

    @{all_pods}=  Oc Get    kind=Pod    namespace=${project_title}    label_selector=component=data-science-pipelines
    Run Keyword And Continue On Failure    Length Should Be    ${all_pods}    7

    @{pipeline_api_server}=  Oc Get    kind=Pod    namespace=${project_title}    label_selector=app=ds-pipeline-dspa
    ${containerNames}=  Create List  oauth-proxy    ds-pipeline-api-server
    Verify Deployment    ${pipeline_api_server}  1  2  ${containerNames}

    @{pipeline_metadata_envoy}=  Oc Get    kind=Pod    namespace=${project_title}    label_selector=app=ds-pipeline-metadata-envoy-dspa
    ${containerNames}=  Create List  container    oauth-proxy
    Verify Deployment    ${pipeline_metadata_envoy}  1  2  ${containerNames}

    @{pipeline_metadata_grpc}=  Oc Get    kind=Pod    namespace=${project_title}    label_selector=app=ds-pipeline-metadata-grpc-dspa
    ${containerNames}=  Create List  container
    Verify Deployment    ${pipeline_metadata_grpc}  1  1  ${containerNames}

    @{pipeline_persistenceagent}=  Oc Get    kind=Pod    namespace=${project_title}    label_selector=app=ds-pipeline-persistenceagent-dspa
    ${containerNames}=  Create List  ds-pipeline-persistenceagent
    Verify Deployment    ${pipeline_persistenceagent}  1  1  ${containerNames}

    @{pipeline_scheduledworkflow}=  Oc Get    kind=Pod    namespace=${project_title}    label_selector=app=ds-pipeline-scheduledworkflow-dspa
    ${containerNames}=  Create List  ds-pipeline-scheduledworkflow
    Verify Deployment    ${pipeline_scheduledworkflow}  1  1  ${containerNames}

    @{pipeline_workflow_controller}=  Oc Get    kind=Pod    namespace=${project_title}    label_selector=app=ds-pipeline-workflow-controller-dspa
    ${containerNames}=  Create List  ds-pipeline-workflow-controller
    Verify Deployment    ${pipeline_workflow_controller}  1  1  ${containerNames}

    @{mariadb}=  Oc Get    kind=Pod    namespace=${project_title}    label_selector=app=mariadb-dspa
    ${containerNames}=  Create List  mariadb
    Verify Deployment    ${mariadb}  1  1  ${containerNames}