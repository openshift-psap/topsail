#!/usr/bin/env python3
import sys
import time

import jwt

# based on https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app#example-using-python-to-generate-a-jwt


def generate_encoded_jwt(pem, client_id):
    # Open PEM
    with open(pem, 'rb') as pem_file:
        signing_key = pem_file.read()

    payload = {
        # Issued at time
        'iat': int(time.time()),
        # JWT expiration time (10 minutes maximum)
        'exp': int(time.time()) + 600,

        # GitHub App's client ID
        'iss': client_id
    }

    # Create JWT
    return jwt.encode(payload, signing_key, algorithm='RS256')

if __name__ == "__main__":
    # Get PEM file path
    if len(sys.argv) > 1:
        pem = sys.argv[1]
    else:
        pem = input("Enter path of private PEM file: ")

    # Get the Client ID
    if len(sys.argv) > 2:
        client_id = sys.argv[2]
    else:
        client_id = input("Enter your Client ID: ")

    encoded_jwt = generate_encoded_jwt(pem, client_id)

    print(f"JWT:  {encoded_jwt}")
