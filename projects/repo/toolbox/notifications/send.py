import os
import logging
import pathlib

import projects.repo.toolbox.notifications.github.api as github_api
import projects.repo.toolbox.notifications.slack.api as slack_api


def send_job_completion_notification(reason, status, github=True, slack=False):
    if os.environ.get("TOPSAIL_LOCAL_CI_MULTI") == "true":
        logging.info("No notification to send from Local-CI multi.")
        # this avoid sending spurious messages ...
        return

    if os.environ.get("TOPSAIL_LOCAL_CI") == "true":
        github = False # don't post notifications to github for LOCAL-CI runs. They stay private.
        slack = False # don't send them to slack either, link/pr_number helpers not implemented yet

    pr_number = get_pr_number()
    artifacts_link = get_artifacts_link()

    if os.environ.get("PERFLAB_CI") == "true" and not pr_number:
        github = False

    failed = False
    if github and not send_job_completion_notification_to_github(reason, status, pr_number, artifacts_link):
        failed = True

    if slack and not send_job_completion_notification_to_slack(reason, status, pr_number, artifacts_link):
        failed = True

    return failed

###

def send_job_completion_notification_to_github(reason, status, pr_number, artifacts_link):
    message = get_github_notification_message(reason, status, pr_number, artifacts_link)

    org, repo = get_org_repo()
    pem_file, client_id = get_github_secrets()
    abort = False

    if None in (pr_number,):
        logging.error("Cannot figure out the PR number")
        abort = True

    if None in (org, repo):
        logging.error("Cannot access the org/repo")
        abort = True

    if None in (pem_file, client_id):
        logging.error("Cannot access the secret files")
        abort = True

    if abort:
        logging.error("Aborting due to previous error(s).")
        return

    user_token = github_api.get_user_token(pem_file, client_id, org, repo)
    resp = github_api.send_notification(org, repo, user_token, pr_number, message)

    if not resp.ok:
        logging.fatal(f"Github notification post failed :/ {resp.text}")

    return resp.ok


def get_github_notification_message(reason, status, pr_number, artifacts_link):
    message=f"""\
**{status}**

* Link to the [test results]({artifacts_link}).
"""
    if (pathlib.Path(os.environ.get("ARTIFACTS_DIR", "")) / "reports_index.html").exists():
        message += f"""
* Link to the [reports index]({artifacts_link}/reports_index.html).
"""
    else:
        message += f"""
* No reports index generated...
"""

    if (var_over := pathlib.Path(os.environ.get("ARTIFACTS_DIR", "")) / "variable_overrides").exists():
        with open(var_over) as f:
            message += f"""
**Test configuration**:
```
{f.readlines().strip()}
```
"""
    else:
        message += """
* Not test configuration (`variable_overrides`) available.
"""
    if os.environ.get("PERFLAB_CI") == "true":
        message += """
*[Test ran on the internal Perflab CI]*
"""

    message += """
*[TOPSAIL auto-generated message]*
"""

    return message


def get_slack_notification_message(reason, status, pr_number, artifacts_link):
    message=f"""\
**{status}**

* Link to the <{artifacts_link}|test results>.
"""
    if (pathlib.Path(os.environ.get("ARTIFACTS_DIR", "")) / "reports_index.html").exists():
        message += f"""
* Link to the <{artifacts_link}/reports_index.html|reports index>.
"""
    else:
        message += f"""
* No reports index generated...
"""

    if (var_over := pathlib.Path(os.environ.get("ARTIFACTS_DIR", "")) / "variable_overrides").exists():
        with open(var_over) as f:
            message += f"""
**Test configuration**:
```
{f.readlines().strip()}
```
"""
    else:
        message += """
* Not test configuration (`variable_overrides`) available.
"""
    if os.environ.get("PERFLAB_CI") == "true":
        message += """
*[Test ran on the internal Perflab CI]*
"""

    message += """
*[TOPSAIL auto-generated message]*
"""

    return message


def send_job_completion_notification_to_slack(reason, status, pr_number, artifacts_link):
    client = slack_api.init_client()
    org, repo = get_org_repo()

    main_ts = slack_api.search_message(client, org, repo, pr_number)
    message = "test message"

    if not main_ts:
        main_ts = slack_api.send_message(client, pr_number=pr_number)  # sends default message
        _, ok = slack_api.send_message(client, message=message, main_ts=main_ts)
    else:
        _, ok = slack_api.send_message(client, message=message, main_ts=main_ts)

    return ok

###

def genetate_github_message():
    pr_number = get_pr_number()
    link = get_artifacts_link()

###

def get_pr_number():
    if os.environ.get("OPENSHIFT_CI") == "true":
        return os.environ["PULL_NUMBER"]

    elif os.environ.get("PERFLAB_CI") == "true":
        git_ref = os.environ["PERFLAB_GIT_REF"]
        if not git_ref.startswith("refs/pull/"):
            logging.debug("Perflab job not running from a PR, no PR number available.")
            return

        return git_ref.split("/")[2]

    elif os.environ.get("TOPSAIL_LOCAL_CI") == "true":
        logging.warning("LocalCI PR number not supported yet.")
        return

    else:
        logging.warning("Test not running from a well-known CI engine, cannot extract a PR number.")
        return


def get_artifacts_link():
    if os.environ.get("OPENSHIFT_CI") == "true":
        test_name = os.environ["HOSTNAME"].removeprefix(os.environ['JOB_NAME_SAFE']+"-")

        return (f"https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/pr-logs/" +
                f"pull/{os.environ['REPO_OWNER']}_{os.environ['REPO_NAME']}/{os.environ['PULL_NUMBER']}" +
                f"/{os.environ['JOB_NAME']}/{os.environ['BUILD_ID']}/artifacts/{os.environ['JOB_NAME_SAFE']}/{test_name}/artifacts/")


    elif os.environ.get("PERFLAB_CI") == "true":
        artifact_dir = os.environ['ARTIFACT_DIR'].removeprefix("/logs/artifacts/")

        return (f"https://{os.environ['JENKINS_INSTANCE']}/{os.environ['JENKINS_JOB']}/{os.environ['JENKINS_BUILD_NUMBER']}/" +
                f"artifact/run/{os.environ['JENKINS_JUMPHOST']}/{artifact_dir})")
    elif os.environ.get("TOPSAIL_LOCAL_CI") == "true":
        logging.warning("LocalCI links not supported yet.")
        return
    else:
        logging.warning("Test not running from a well-known CI engine, cannot extract the artifacts link.")

        return None

def get_org_repo():
    if os.environ.get("OPENSHIFT_CI") == "true":
        return os.environ['REPO_OWNER'], os.environ['REPO_NAME']
    else:
        return "openshift-psap", "topsail"

def get_github_secrets():
    if not os.environ.get("PSAP_ODS_SECRET_PATH"):
        logging.warning("PSAP_ODS_SECRET_PATH not defined, cannot access the Github secrets")
        return None, None

    secret_dir = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH"))
    pem_file = secret_dir / "topsail-bot.2024-09-18.private-key.pem"
    client_id_file = secret_dir / "topsail-bot.clientid"

    if not (pem_file.exists() and client_id_file.exists()):
        if not pem_file.exists():
            logging.warning(f"Github App private key does not exists ({pem_file})")
        else:
            logging.warning(f"Github App clientid file does not exists ({client_id_file})")
        return None, None

    with open(client_id_file) as f:
        client_id = f.read().strip()

    return pem_file, client_id
