import logging
import os
import pathlib
import requests

from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


CHANNEL_ID = "C07NS5TAKPA"
DEFAULT_MESSAGE = "🧵 Thread for PR #{}"


def fetch_pr_creation_time(org: str, repo: str, pr_number: str, user_token: str):
    """Fetch the PR creation time to filter out Slack messages."""
    headers = {
        "Authorization": f"Bearer {user_token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    url = f"https://api.github.com/repos/{org}/{repo}/pulls/{pr_number}"

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        pr_data = response.json()
        created_at = pr_data["created_at"]
        return datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").timestamp()

    else:
        logging.error(f"Error fetching PR creation time: {response.text}")


def search_message(client, org: str, repo: str, pr_number: str, user_token: str):
    """Searches for a message matching the pattern.
    Returns thread ts if successful."""
    has_more = False
    history = []
    cursor = None

    pr_created_at = fetch_pr_creation_time(org, repo, pr_number, user_token)

    while not has_more:
        try:
            result = client.conversations_history(
                channel=CHANNEL_ID,
                limit=20,  # default 100
                oldest=pr_created_at,
                cursor=cursor,
            )

            history = result["messages"]
            has_more = result["has_more"]
            if has_more:
                cursor = result["response_metadata"][
                    "next_cursor"
                ]  # in case it is not in the first 20

        except SlackApiError as e:
            logging.warning(f"Error fetching history: {e}")
            return None

        for message in history:
            if pr_number in message["text"]:
                return message["ts"]

    return None


def send_message(
    client, message: str = None, pr_number: str = None, main_ts: str = None
):
    """Sends a message. Optionally to a thread."""
    if not message:
        message = DEFAULT_MESSAGE.format(pr_number)

    try:
        result = client.chat_postMessage(
            channel=CHANNEL_ID,
            text=message,
            thread_ts=main_ts,
        )

    except SlackApiError as e:
        logging.warning(f"Error posting message: {e}")
        return None, False

    return result["ts"], True


def init_client():
    """Initialize Slack's client."""
    if not os.environ.get("PSAP_ODS_SECRET_PATH"):
        logging.warning(
            "PSAP_ODS_SECRET_PATH not defined, cannot access the Slack secrets"
        )
        return None

    secret_dir = pathlib.Path(os.environ.get("PSAP_ODS_SECRET_PATH"))
    token_file = secret_dir / "topsail-bot.slack-token"

    with open(token_file, "r") as sf:
        client = WebClient(token=sf.read())

    return client
