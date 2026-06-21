"""
auth.py — WorldQuant Brain session management.

Handles standard and biometrics authentication.
Returns a persistent requests.Session with JWT cached.
"""

import json
import requests
from os.path import expanduser
from urllib.parse import urljoin


def create_session(credentials_path: str = "~/.brain_credentials") -> requests.Session:
    """
    Authenticate against the WQ Brain API.

    Supports both standard and biometrics (Persona) auth flows.
    Credentials file should be a JSON array: ["email", "password"]

    Returns:
        Authenticated requests.Session
    """
    s = requests.Session()

    with open(expanduser(credentials_path), "r") as f:
        s.auth = tuple(json.load(f))

    response = s.post("https://api.worldquantbrain.com/authentication")

    if response.status_code == 401:
        auth_type = response.headers.get("WWW-Authenticate", "")
        if auth_type == "persona":
            biometric_url = urljoin(response.url, response.headers["Location"])
            print("Biometrics authentication required.")
            print(f"Open this URL in your browser and complete verification:\n\n  {biometric_url}\n")
            input("Press Enter once you have completed biometrics authentication...")
            s.post(biometric_url)
        else:
            raise PermissionError(
                "Authentication failed. Check your credentials in ~/.brain_credentials"
            )

    elif response.status_code not in (200, 201):
        raise ConnectionError(
            f"Unexpected response from authentication endpoint: {response.status_code}"
        )

    print("✓ Session authenticated successfully.")
    return s


def check_session(s: requests.Session) -> bool:
    """
    Verify the current session is still valid.
    Returns True if authenticated, False if expired.
    """
    response = s.get("https://api.worldquantbrain.com/authentication")
    return response.status_code == 200
