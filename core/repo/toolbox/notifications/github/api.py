import requests
import json
import logging
from datetime import datetime

from . import gen_jwt

COMMON_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

BASE_URL = "https://api.github.com"


def get_user_token(pem_file, client_id, org, repo):
    # Get the encoded JWT

    jwt = gen_jwt.generate_encoded_jwt(pem_file, client_id)

    headers = dict(Authorization=f"Bearer {jwt}") | COMMON_HEADERS

    # Get the installation ID

    installation_resp = requests.get(f"{BASE_URL}/repos/{org}/{repo}/installation", headers=headers)

    installation_id = installation_resp.json()["id"]

    # Get the user token

    access_token_resp = requests.post(f"{BASE_URL}/app/installations/{installation_id}/access_tokens", headers=headers)

    user_token = access_token_resp.json()["token"]

    return user_token


def send_notification(org, repo, user_token, pr_number, message):
    headers = dict(Authorization=f"Bearer {user_token}") | COMMON_HEADERS

    data = dict(body=message)
    data_str = json.dumps(data)

    return requests.post(
        f"{BASE_URL}/repos/{org}/{repo}/issues/{pr_number}/comments",
        data=data_str,
        headers=headers,
    )


def fetch_pr_data(org: str, repo: str, pr_number: str):
    """Fetch the PR creation time to filter out Slack messages.
    No user_token is needed to list PRs of public repositories."""
    url = f"{BASE_URL}/repos/{org}/{repo}/pulls/{pr_number}"

    response = requests.get(url, headers=COMMON_HEADERS)
    if not response.ok:
        logging.warning(f"Error fetching PR creation time: {response.text}")

        return 0, None  # XXX: allow the notifications pipeline still to proceed

    pr_data = response.json()
    created_at = pr_data["created_at"]

    return datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").timestamp(), pr_data


if __name__ == "__main__":
    PEM_FILE = "topsail-bot.2024-09-18.private-key.pem"
    CLIENT_ID_FILE = "client_id"
    ORG = "openshift-psap"
    REPO = "topsail"

    with open(CLIENT_ID_FILE) as f:
        client_id = f.read().strip()

    user_token = get_user_token(PEM_FILE, client_id, ORG, REPO)

    print(user_token)
