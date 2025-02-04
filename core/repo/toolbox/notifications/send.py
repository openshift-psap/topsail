import os
import logging
import pathlib

import projects.repo.toolbox.notifications.github.api as github_api
import projects.repo.toolbox.notifications.slack.api as slack_api


def send_job_completion_notification(reason, status, github=True, slack=False, dry_run=False):
    if os.environ.get("TOPSAIL_LOCAL_CI_MULTI") == "true":
        logging.info("No notification to send from Local-CI multi.")
        # this avoid sending spurious messages ...
        return

    if os.environ.get("TOPSAIL_LOCAL_CI") == "true":
        github = False # don't post notifications to github for LOCAL-CI runs. They stay private.

    pr_number = get_pr_number()

    if os.environ.get("PERFLAB_CI") == "true" and not pr_number:
        github = False

    failed = False
    if github and not send_job_completion_notification_to_github(reason, status, pr_number, dry_run):
        failed = True

    if slack and not send_job_completion_notification_to_slack(reason, status, pr_number, dry_run):
        failed = True

    return failed

###

def send_job_completion_notification_to_github(reason, status, pr_number, dry_run):
    message = get_github_notification_message(reason, status, pr_number)

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
    if dry_run:
        logging.info(f"Github notification:\n{message}")
        logging.info(f"***")
        logging.info(f"***")
        logging.info(f"***\n")

        return True

    resp = github_api.send_notification(org, repo, user_token, pr_number, message)

    if not resp.ok:
        logging.fatal(f"Github notification post failed :/ {resp.text}")

    return resp.ok


def get_github_notification_message(reason, status, pr_number):
    def get_link(name, path, is_raw_file=False, base=None, is_dir=False):
        return f"[{name}]({get_ci_link(path, is_raw_file, base, is_dir)})"

    def get_italics(text):
        return f"*{text}*"

    def get_bold(text):
        return f"**{text}**"

    status_icon = ":red_circle:" if reason == "ERR" \
        else ":green_circle:"

    return get_common_message(reason, f"{status_icon} {status} {status_icon}", get_link, get_italics, get_bold)


def get_common_message(reason, status, get_link, get_italics, get_bold):
    message = ""

    if os.environ.get("PERFLAB_CI") == "true":
        message += get_perflab_ci_extra_header_message(get_link)
        message += "\n\n"
    message += f"""\
{get_bold(status)}
"""

    message  += f"""
• Link to the {get_link("test results", "", is_dir=True)}.
"""
    if (pathlib.Path(os.environ.get("ARTIFACT_DIR", "")) / "reports_index.html").exists():
        message += f"""
• Link to the {get_link("reports index", "reports_index.html")}.
"""
    else:
        message += f"""
• No reports index generated...
"""

    if (var_over := pathlib.Path(os.environ.get("ARTIFACT_DIR", "")) / "variable_overrides.yaml").exists():
        with open(var_over) as f:
            message += f"""
{get_bold("Test configuration")}:
```
{f.read().strip()}
```
"""
    else:
        message += """
• No test configuration (`variable_overrides.yaml`) available.
"""

    if os.environ.get("PERFLAB_CI") == "true":
        message += get_perflab_ci_extra_footer_message(get_link)


    if (failures := pathlib.Path(os.environ.get("ARTIFACT_DIR", "")) / "FAILURES").exists():
        with open(failures) as f:
            HEAD = 10
            lines = f.readlines()

            message += f"""
*{get_link("Failure indicator", "FAILURES", is_raw_file=True)}*:
```
{"".join(lines[:HEAD])}
{"[...]" if len(lines) > HEAD else ""}
```
""" if lines else f"""
*Failure indicator*: Empty. (See {get_link("run.log", "run.log", is_raw_file=True)})
"""

    if os.environ.get("PERFLAB_CI") == "true":
        message += f"""
{get_italics("[Test ran on the internal Perflab CI]")}
"""

    return message

# Warning:
# Slack API messages format is different from the GUI
# https://api.slack.com/reference/surfaces/formatting

def get_slack_thread_message(reason, status, pr_data):
    def get_link(name, path, is_raw_file=False, base=None, is_dir=False):
        return f"<{get_ci_link(path, is_raw_file, base, is_dir)}|{name}>"

    def get_italics(text):
        return f"_{text}_"

    def get_bold(text):
        return f"*{text}*"

    status_icon = ":no-red-circle:" if reason == "ERR" \
        else ":done-circle-check:"

    return get_common_message(reason, f"{status_icon} {status}", get_link, get_italics, get_bold)


def get_slack_channel_message_anchor(pr_number):
    if pr_number:
        return f"Thread for PR #{pr_number}"
    else:
        return "Thread for tests without PRs"


def get_slack_channel_message(anchor: str, pr_data: dict):
    """Generates the Slack's notification main thread message."""

    org, repo = get_org_repo()

    message = f"🧵 {anchor}"

    if not pr_data:
        return message

    # see eg https://api.github.com/repos/openshift-psap/topsail/pulls/362 for the content of 'pr_data'
    message += f"""

```{pr_data['title']}```

Link to the <{pr_data['html_url']}|PR>.
"""

    return message


def send_job_completion_notification_to_slack(reason, status, pr_number, dry_run):
    client = slack_api.init_client()
    if not client:
        return

    org, repo = get_org_repo()

    pr_created_at, pr_data = github_api.fetch_pr_data(org, repo, pr_number)

    anchor = get_slack_channel_message_anchor(pr_number)

    channel_msg_ts, channel_message = slack_api.search_channel_message(client, anchor, not_before=pr_created_at)

    if not channel_msg_ts:
        channel_message = get_slack_channel_message(anchor, pr_data)

        if dry_run:
            logging.info(f"Posting Slack channel notification ...")
        else:
            channel_msg_ts = slack_api.send_message(client, message=channel_message)


    if dry_run:
        logging.info(f"Slack channel notification:\n{channel_message}")

    thread_message = get_slack_thread_message(reason, status, pr_data)

    if dry_run:
        logging.info(f"Slack thread notification:\n{thread_message}")
        logging.info(f"***")
        logging.info(f"***")
        logging.info(f"***\n")

        return True

    _, ok = slack_api.send_message(client, message=thread_message, main_ts=channel_msg_ts)

    return ok


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
        return os.environ["PULL_NUMBER"]

    else:
        logging.warning("Test not running from a well-known CI engine, cannot extract a PR number.")
        return


# returns a tuple (base_link, link_suffix)
def get_ci_base_link(is_raw_file=False, is_dir=False):
    if os.environ.get("OPENSHIFT_CI") == "true":
        test_path = os.environ["TOPSAIL_OPENSHIFT_CI_STEP_DIR"]

        return ((f"https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/pr-logs/" +
                 f"pull/{os.environ['REPO_OWNER']}_{os.environ['REPO_NAME']}/{os.environ['PULL_NUMBER']}" +
                 f"/{os.environ['JOB_NAME']}/{os.environ['BUILD_ID']}/artifacts/{os.environ['JOB_NAME_SAFE']}/{test_path}"),
                "")


    elif os.environ.get("PERFLAB_CI") == "true":
        artifact_dir = os.environ['ARTIFACT_DIR'].removeprefix("/logs/artifacts")

        return ((f"https://{os.environ['JENKINS_INSTANCE']}/{os.environ['JENKINS_JOB']}/{os.environ['JENKINS_BUILD_NUMBER']}/" +
                f"artifact/run/{os.environ['JENKINS_JUMPHOST']}/{artifact_dir}"),
                ("/*view*/" if is_raw_file else ""))

    elif os.environ.get("TOPSAIL_LOCAL_CI") == "true":
        bucket_name = os.environ.get("TOPSAIL_LOCAL_CI_BUCKET_NAME")
        job_name_safe = os.environ.get("JOB_NAME_SAFE")
        run_id = os.environ.get("TEST_RUN_IDENTIFIER")

        return f"https://{bucket_name}.s3.amazonaws.com/{'index.html#' if is_dir else ''}local-ci/{job_name_safe}/{run_id}{'/' if is_dir else ''}", ""
    else:
        logging.warning("Test not running from a well-known CI engine, cannot extract the artifacts link.")

        return None, None


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


def get_ci_link(path, is_raw_file=False, base=None, is_dir=False):
    if base is None:
        base, suffix = get_ci_base_link(is_raw_file, is_dir)
    else:
        suffix = None

    link = base + (f"/{path}" if path else "") + (suffix if suffix else "")

    return link


def get_perflab_ci_extra_header_message(get_link):
    return f"```Jenkins Job #{os.environ['JENKINS_BUILD_NUMBER']}```"


def get_perflab_ci_extra_footer_message(get_link):
    base = get_ci_base_link()[0].partition("/artifact/run")[0]
    link = f"rebuild/parameterized"

    return f"""
• Link to the {get_link("Rebuild page", link, base=base)}.
"""
