"""
OAuth2 authentication for Google Gemini API.

Supports three auth methods (in priority order):
  1. Stored OAuth token (~/.config/dlm/oauth_token.json)
  2. API key (GOOGLE_API_KEY in config or environment)
  3. Application Default Credentials (if gcloud is set up)

Run `dlm-auth` to authenticate via OAuth (opens browser).
"""

import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_PATH = Path.home() / ".config" / "dlm" / "oauth_token.json"
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def get_credentials(client_id=None, client_secret=None):
    """Load stored OAuth credentials, refreshing if expired.

    Returns Credentials object or None if no stored token.
    """
    if not TOKEN_PATH.exists():
        return None

    try:
        with open(TOKEN_PATH) as f:
            token_data = json.load(f)

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id or token_data.get("client_id"),
            client_secret=client_secret or token_data.get("client_secret"),
            scopes=SCOPES,
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_credentials(creds)

        return creds
    except Exception as e:
        print(f"Warning: Could not load OAuth credentials: {e}")
        return None


def run_auth_flow(client_id, client_secret):
    """Run interactive OAuth flow (opens browser). Returns Credentials."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds)
    return creds


def _save_credentials(creds):
    """Save credentials to disk (chmod 600)."""
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }
    with open(TOKEN_PATH, "w") as f:
        json.dump(token_data, f, indent=2)
    TOKEN_PATH.chmod(0o600)


def auth_command():
    """CLI entry point for `dlm-auth`."""
    from .settings import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("OAuth client credentials not configured.")
        print()
        print("To set up OAuth:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create a project (or use existing)")
        print("  3. Enable the 'Generative Language API'")
        print("  4. Create OAuth Client ID (type: Desktop app)")
        print("  5. Add to ~/.config/dlm/config.py:")
        print()
        print('     GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"')
        print('     GOOGLE_CLIENT_SECRET = "your-client-secret"')
        print()
        print("  Then run `dlm-auth` again.")
        return

    # Check if already authenticated
    creds = get_credentials(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
    if creds and not creds.expired:
        print("✓ Already authenticated with Google.")
        print(f"  Token stored at: {TOKEN_PATH}")
        print("  Run `dlm-auth --reauth` to re-authenticate.")
        import sys
        if "--reauth" not in sys.argv:
            return

    print("Opening browser for Google OAuth...")
    print("(Sign in with your Google / AI Pro account)")
    print()

    try:
        creds = run_auth_flow(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
        print()
        print("✓ Authenticated! Token saved to:")
        print(f"  {TOKEN_PATH}")
        print()
        print("DLM will now use your Google account for Gemini API calls.")
    except Exception as e:
        print(f"Authentication failed: {e}")
