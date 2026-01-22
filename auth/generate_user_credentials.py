# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This script is adapted from an example provided in the
# Google Ads Python Client Library:
# https://github.com/googleads/google-ads-python
# The original example is also licensed under the Apache License, Version 2.0.
"""This example will create an OAuth2 refresh token for the Google Ads API, SA360 Reporting API, Google Sheet and CloudPlatform.

This example works with both web and desktop app OAuth client ID types.

https://console.cloud.google.com

IMPORTANT: For web app clients types, you must add "http://127.0.0.1" to the
"Authorized redirect URIs" list in your Google Cloud Console project before
running this example. Desktop app client types do not require the local
redirect to be explicitly configured in the console.

Once complete, download the credentials and save the file path so it can be
passed into this example.

This example is a very simple implementation, for a more detailed example see:
https://developers.google.com/identity/protocols/oauth2/web-server#python
"""

from typing import List, Dict

import argparse
import hashlib
import os
import re
import socket
import sys
from urllib.parse import unquote

# If using Web flow, the redirect URL must match exactly what’s configured in GCP for
# the OAuth client.  If using Desktop flow, the redirect must be a localhost URL and
# is not explicitly set in GCP.
from google_auth_oauthlib.flow import Flow

_SCOPE = [
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/doubleclicksearch",
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/spreadsheets",
]
_SERVER = "127.0.0.1"
_PORT = 8080
_REDIRECT_URI = f"http://{_SERVER}:{_PORT}"


def main(client_secrets_path: str, scopes: List[str]) -> None:
    """The main method, starts a basic server and initializes an auth request.

    Args:
        client_secrets_path: a path to where the client secrets JSON file is
          located on the machine running this example.
        scopes: a list of API scopes to include in the auth request, see:
            https://developers.google.com/identity/protocols/oauth2/scopes
    """
    # Join scopes into a space-delimited string
    scopes_str = " ".join(scopes)
    flow = Flow.from_client_secrets_file(client_secrets_path, scopes=scopes_str)
    flow.redirect_uri = _REDIRECT_URI

    # Create an anti-forgery state token as described here:
    # https://developers.google.com/identity/protocols/OpenIDConnect#createxsrftoken
    passthrough_val = hashlib.sha256(os.urandom(1024)).hexdigest()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        state=passthrough_val,
        prompt="consent",
        include_granted_scopes="true",
    )

    # Prints the authorization URL so you can paste into your browser. In a
    # typical web application you would redirect the user to this URL, and they
    # would be redirected back to "redirect_url" provided earlier after
    # granting permission.
    print("Paste this URL into your browser: ")
    print(authorization_url)
    print(f"\nWaiting for authorization and callback to: {_REDIRECT_URI}")

    # Retrieves an authorization code by opening a socket to receive the
    # redirect request and parsing the query parameters set in the URL.
    code = unquote(get_authorization_code(passthrough_val))

    # Pass the code back into the OAuth module to get a refresh token.
    flow.fetch_token(code=code)
    refresh_token = flow.credentials.refresh_token

    print(f"Your refresh token is: {refresh_token}\n")
    print(
        "Add your refresh token to your client library configuration as "
        "described here: "
        "https://developers.google.com/google-ads/api/docs/client-libs/python/configuration"
    )


def get_authorization_code(passthrough_val: str) -> str:
    """Opens a socket to handle a single HTTP request containing auth tokens.

    Args:
        passthrough_val: an anti-forgery token used to verify the request
          received by the socket.

    Returns:
        a str access token from the Google Auth service.
    """
    # Open a socket at _SERVER:_PORT and listen for a request
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((_SERVER, _PORT))
        s.listen()
        print(f"Server listening on {_REDIRECT_URI}")

        while True: # Keep listening until we get the code
            conn, addr = s.accept()
            print(f"Connected by {addr}")
            data = conn.recv(2048)  # Increased buffer size
            if not data:
                conn.close()
                continue

            decoded = data.decode("utf-8")

            if decoded.startswith("GET /?"):
                params = parse_raw_query_params(data)
                if "code" in params and "state" in params:
                    if params.get("state") == passthrough_val:
                        send_response(conn, "Authorization code received! You can close this window.")
                        conn.close()
                        return params["code"]
                    else:
                        send_response(conn, "Error: State parameter mismatch.")
                else:
                    send_response(conn, "Error: Missing 'code' or 'state' in callback.")
            elif "GET /favicon.ico" in decoded:
                 send_response(conn, "", status="404 Not Found")
            else:
                send_response(conn, "Ignoring request.", status="400 Bad Request")
            
            conn.close()
    return None # Should not be reached if successful

def send_response(conn, body, status="200 OK"):
    response = (
        f"HTTP/1.1 {status}\r\n"
        "Content-Type: text/html\r\n\r\n"
        f"<b>{body}</b>"
        "<p>Please check the console output.</p>\r\n"
    )
    conn.sendall(response.encode())


def parse_raw_query_params(data: bytes) -> Dict[str, str]:
    """Parses a raw HTTP request to extract its query params as a dict.

    Note that this logic is likely irrelevant if you're building OAuth logic
    into a complete web application, where response parsing is handled by a
    framework.

    Args:
        data: raw request data as bytes.

    Returns:
        a dict of query parameter key value pairs.
    """
    # Decode the request into a utf-8 encoded string
    decoded = data.decode("utf-8")
    # Use a regular expression to extract the URL query parameters string
    match = re.search(r"GET\s+\/\?(.*?) HTTP", decoded)
    if not match:
        print(f"Could not find parameters in request: {decoded}")
        return {}
    params = match.group(1)
    # Split the parameters to isolate the key/value pairs
    pairs = [pair.split("=") for pair in params.split("&")]
    # Convert pairs to a dict to make it easy to access the values
    return {key: val for key, val in pairs}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Generates OAuth2 refresh token using the Web application flow. "
            "To retrieve the necessary client_secrets JSON file, first "
            "generate OAuth 2.0 credentials of type Web application in the "
            "Google Cloud Console (https://console.cloud.google.com). "
            "Make sure 'http://_SERVER:_PORT' is included the list of "
            "'Authorized redirect URIs' for this client ID."
        ),
    )
    # The following argument(s) should be provided to run the example.
    parser.add_argument(
        "-c",
        "--client_secrets_path",
        required=True,
        type=str,
        help=(
            "Path to the client secrets JSON file from the Google Developers "
            "Console that contains your client ID, client secret, and "
            "redirect URIs."
        ),
    )
    parser.add_argument(
        "--additional_scopes",
        default=None,
        type=str,
        nargs="+",
        help="Additional scopes to apply when generating the refresh token.",
    )
    args = parser.parse_args()

    configured_scopes = list(_SCOPE)  # Create a copy of the _SCOPE list

    if args.additional_scopes:
        configured_scopes.extend(args.additional_scopes)

    main(args.client_secrets_path, configured_scopes)
