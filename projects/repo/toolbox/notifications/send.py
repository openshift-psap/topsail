import os
import logging
import pathlib
import json
import yaml

import projects.repo.toolbox.notifications.github.api as github_api
import projects.repo.toolbox.notifications.slack.api as slack_api

GITHUB_APP_PEM_FILE = "topsail-bot.2024-09-18.private-key.pem"
GITHUB_APP_CLIENT_ID_FILE = "topsail-bot.clientid"
SLACK_TOKEN_FILE = "topsail-bot.slack-token"

def get_secrets():
    # currently hardcoded, because there's no configuration file at this level
    SECRET_ENV_KEYS = ("PSAP_ODS_SECRET_PATH", "CRC_MAC_AI_SECRET_PATH", "CONTAINER_BENCH_SECRET_PATH")

    secret_env_key = None
    warn = []
    for secret_env_key in SECRET_ENV_KEYS:
        if os.environ.get(secret_env_key): break
        warn.append(f"{secret_env_key} not defined, cannot access the Github secrets")
    else:
        for warning in warn:
            logging.warning(warning)
        return None, None

    secret_dir = pathlib.Path(os.environ[secret_env_key])
    if not secret_dir.exists():
        logging.fatal(f"{secret_env_key} points to a non-existing directory ...")
        return None, None

    return secret_dir, secret_env_key


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

    if os.environ.get("JOB_TYPE") == "periodic":
        logging.info("Running from a Periodic job, don't send notification to github")
        github = False

    secret_dir, secret_env_key = get_secrets()
    if secret_dir is None:
        return True

    failed = False
    if github and not send_job_completion_notification_to_github(
            *get_github_secrets(secret_dir, secret_env_key),
            reason, status, pr_number, dry_run):

        failed = True

    if slack and not send_job_completion_notification_to_slack(
            get_slack_secrets(secret_dir, secret_env_key),
            reason, status, pr_number, dry_run):
        failed = True

    return failed

###

def send_job_completion_notification_to_github(pem_file, client_id, reason, status, pr_number, dry_run):
    message = get_github_notification_message(reason, status, pr_number)

    org, repo = get_org_repo()

    abort = False

    if None in (pr_number,):
        logging.error("github: Cannot figure out the PR number")
        abort = True

    if None in (org, repo):
        logging.error("github: Cannot access the org/repo")
        abort = True

    if None in (pem_file, client_id):
        logging.error("github: Cannot access the secret files")
        abort = True

    if abort:
        logging.error("github: Aborting due to previous error(s).")
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

def get_slack_thread_message(reason, status):
    def get_link(name, path, is_raw_file=False, base=None, is_dir=False):
        return f"<{get_ci_link(path, is_raw_file, base, is_dir)}|{name}>"

    def get_italics(text):
        return f"_{text}_"

    def get_bold(text):
        return f"*{text}*"

    status_icon = ":no-red-circle:" if reason == "ERR" \
        else ":done-circle-check:"

    return get_common_message(reason, f"{status_icon} {status}", get_link, get_italics, get_bold)


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


def send_job_completion_notification_to_slack(
        token, reason, status, pr_number, dry_run,
):
    if not token:
        return

    client = slack_api.init_client(token)
    if not client:
        return False

    org, repo = get_org_repo()
    is_periodic = False
    if pr_number:
        pr_created_at, pr_data = github_api.fetch_pr_data(org, repo, pr_number)
        anchor = f"Thread for PR #{pr_number}"
    elif os.environ.get("JOB_TYPE") == "periodic":
        pr_created_at = None
        periodic_name = os.environ["JOB_NAME_SAFE"]
        anchor = f"Thread for Periodic job `{periodic_name}`"
        is_periodic = True
    else:
        pr_created_at = None
        anchor = "Thread for tests without PRs"

    channel_msg_ts, channel_message = slack_api.search_channel_message(client, anchor, not_before=pr_created_at)

    if not channel_msg_ts:
        if is_periodic:
            channel_message = anchor
        else:
            channel_message = get_slack_channel_message(anchor, pr_data)

        if dry_run:
            logging.info(f"Posting Slack channel notification ...")
        else:
            channel_msg_ts, ok = slack_api.send_message(client, message=channel_message)
            if not ok:
                return True


    if dry_run:
        logging.info(f"Slack channel notification:\n{channel_message}")

    thread_message = get_slack_thread_message(reason, status)

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
        return os.environ.get("PULL_NUMBER")

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
        job_spec = json.loads(os.environ["JOB_SPEC"])

        test_name = os.environ['JOB_NAME_SAFE']
        test_path = os.environ["TOPSAIL_OPENSHIFT_CI_STEP_DIR"]
        job = job_spec["job"]
        build_id = job_spec["buildid"]

        if job_spec["type"] == "periodic":
            link_path = f"logs/{job}/{build_id}"

        else:
            pull_number = job_spec["refs"]["pulls"][0]["number"]
            github_org = job_spec["refs"]["org"]
            github_repo = job_spec["refs"]["repo"]

            link_path = f"pr-logs/pull/{github_org}_{github_repo}/{pull_number}/{job}/{build_id}"

        return ((f"https://gcsweb-ci.apps.ci.l2s4.p1.openshiftapps.com/gcs/test-platform-results/"
                 + link_path
                 + f"/artifacts/{test_name}/{test_path}",
                 ""))

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

        return "https://no_known_ci_engine/", "?no_ext=true"


def get_org_repo():
    return os.environ.get('REPO_OWNER', "openshift-psap"), os.environ.get('REPO_NAME', "topsail")


def get_github_secrets(secret_dir, secret_env_key):
    pem_file = secret_dir / GITHUB_APP_PEM_FILE
    client_id_file = secret_dir / GITHUB_APP_CLIENT_ID_FILE

    if not pem_file.exists():
        logging.warning(f"Github App private key does not exists ({pem_file}) in {secret_env_key}")
        return None, None

    if not client_id_file.exists():
        logging.warning(f"Github App clientid file does not exists ({client_id_file}) in {secret_env_key}")
        return None, None

    client_id_content = client_id_file.read_text().strip()

    return pem_file, client_id_content


def get_slack_secrets(secret_dir, secret_env_key):
    token_file = secret_dir / SLACK_TOKEN_FILE

    if not token_file.exists():
        logging.warning(f"{token_file.name} not found in {secret_env_key}. "
                        "Cannot send the Slack notification")
        return None

    return token_file.read_text()


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


""" # example of a regression_summary file:
entries_count: 3
failures: 0
kpis_count: 2
message: Performed 6 KPI regression analyses over 3 entries x 2 KPIs. 0 KPIs didn't
  pass.
no_history: 0
not_analyzed: 0
significant_performance_increase: 0
total_points: 6
"""

def send_cpt_notification(
        regression_summary_path, title, slack, dry_run
):
    summary_path = pathlib.Path(regression_summary_path)
    if not summary_path.exists():
        logging.fatal(f"Regression summary doesn't exist :/ ({regression_summary_path})")
        return True

    try:
        with open(summary_path) as f:
            summary = yaml.safe_load(f)
    except Exception as e:
        logging.fatal(f"Failed to load regression summary: {e}")
        return True

    secret_dir, secret_env_key = get_secrets()
    if secret_dir is None:
        return True

    failed = False
    if slack:
        failed = send_cpt_notification_to_slack(secret_dir, secret_env_key, title, summary, dry_run)

    return failed


def send_cpt_notification_to_slack(secret_dir, secret_env_key, title, summary, dry_run):
    token = get_slack_secrets(secret_dir, secret_env_key)
    if not token:
        return True

    client = slack_api.init_client(token)
    if not client:
        logging.fatal("Couldn't get the slack client ...")
        return True

    channel_msg_ts, channel_message = slack_api.search_channel_message(client, title)

    if not channel_msg_ts:
        channel_message = f"🧵 Thread for `{title}` continuous performance testing"
        if dry_run:
            logging.info(f"Posting Slack channel notification ...\n{channel_message}")
        else:
            channel_msg_ts = slack_api.send_message(client, message=channel_message)

    try:
        thread_message = get_slack_cpt_message(summary)
    except Exception as e:
        logging.fatal(f"Failed to generate the slack notification message: {e}")
        return True

    if dry_run:
        logging.info(f"Posting Slack thread notification ...\n{thread_message}")
        ok = True
    else:
        _, ok = slack_api.send_message(client, message=thread_message, main_ts=channel_msg_ts)

    return not ok


def get_slack_cpt_message(summary):
    def get_link(name, path, is_raw_file=False, base=None, is_dir=False):
        return f"<{get_ci_link(path, is_raw_file, base, is_dir)}|{name}>"

    def get_italics(text):
        return f"_{text}_"

    def get_bold(text):
        return f"*{text}*"

    status_icon = ":no-red-circle:" if summary.get("failures") \
        else ":done-circle-check:"

    return f"""{status_icon} {get_bold(summary['message'])}

• Link to the {get_link("test results", "", is_dir=True)}.
• Link to the {get_link("reports index", "reports_index.html")}.

- `{summary['entries_count']}` entries were tested against `{summary['kpis_count']}` KPIs
- `{summary['failures']}` failed
- `{summary['no_history']}` had no history
- `{summary['not_analyzed']}` were not analyzed
- `{summary['significant_performance_increase']}` had a significant performance degradation
- `{summary['total_points']}` points were checked for regression.
    """
