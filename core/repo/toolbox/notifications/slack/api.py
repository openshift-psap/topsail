import logging
import os
import pathlib

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


CHANNEL_ID = "C07NS5TAKPA"
MAX_CALLS = 10


def search_channel_message(client, message_anchor: str, not_before):
    """Searches for a message matching the pattern.
    Returns thread ts if successful."""
    has_more = True
    history = []
    cursor = None
    calls = 0

    while has_more and calls < MAX_CALLS:
        calls += 1

        try:
            result = client.conversations_history(
                channel=CHANNEL_ID,
                limit=20,  # default 100
                oldest=not_before,
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
            return None, None

        for message in history:
            if message_anchor not in message["text"]:
                continue

            return message["ts"], message["text"]

    if calls == MAX_CALLS:
        logging.info(f"Slack text search stopped due to MAX_CALLS ({MAX_CALLS}) exceeded.")

    return None, None


def send_message(client, message: str, main_ts: str = None):
    """Sends a message. Optionally to a thread."""
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
