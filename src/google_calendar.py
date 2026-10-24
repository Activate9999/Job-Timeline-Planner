from __future__ import print_function

import json
import os.path
from pathlib import Path

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendar:

    class AuthorizationRequired(RuntimeError):
        """The hosted user must complete the configured web OAuth flow."""

    def __init__(self):

        self.service = self.authenticate()

    def authenticate(self):

        creds = None

        project_root = Path(__file__).resolve().parent.parent
        token_path = Path(os.environ.get("GOOGLE_TOKEN_PATH", project_root / "credentials" / "token.json"))
        credentials_path = Path(os.environ.get("GOOGLE_CLIENT_SECRETS_FILE", project_root / "credentials" / "credentials.json"))
        hosted_client = os.environ.get("GOOGLE_OAUTH_CLIENT_CONFIG")

        if os.path.exists(token_path):

            creds = Credentials.from_authorized_user_file(
                token_path,
                SCOPES
            )

        if not creds or not creds.valid:

            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    # Revoked/expired refresh tokens require the user to consent again.
                    if hosted_client:
                        raise self.AuthorizationRequired("Google Calendar access needs to be renewed.")
                    creds = self._authorize(credentials_path)

            else:

                if hosted_client:
                    raise self.AuthorizationRequired("Connect Google Calendar to continue.")

                if not os.path.exists(credentials_path):
                    raise RuntimeError(
                        "Google Calendar is not configured. Add credentials/credentials.json from Google Cloud Console."
                    )

                creds = self._authorize(credentials_path)

            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, "w", encoding="utf-8") as token:

                token.write(creds.to_json())

        service = build("calendar", "v3", credentials=creds)

        return service

    @staticmethod
    def _authorize(credentials_path):
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        return flow.run_local_server(port=0, open_browser=True)

    @staticmethod
    def web_client_config():
        raw = os.environ.get("GOOGLE_OAUTH_CLIENT_CONFIG")
        return json.loads(raw) if raw else None

    @staticmethod
    def token_path():
        project_root = Path(__file__).resolve().parent.parent
        return Path(os.environ.get("GOOGLE_TOKEN_PATH", project_root / "credentials" / "token.json"))

    def create_event(self, title, date):

        event = {

            "summary": title,

            "start": {

                "date": date,

                "timeZone": "Asia/Kolkata"

            },

            "end": {

                "date": date,

                "timeZone": "Asia/Kolkata"

            },

            "reminders": {

                "useDefault": False,

                "overrides": [

                    {

                        "method": "popup",

                        "minutes": 1440

                    },

                    {

                        "method": "popup",

                        "minutes": 60

                    }

                ]

            }

        }

        created = self.service.events().insert(

            calendarId="primary",

            body=event

        ).execute()

        return created["id"]

    def delete_event(self, event_id):
        self.service.events().delete(calendarId="primary", eventId=event_id).execute()


if __name__ == "__main__":

    calendar = GoogleCalendar()

    calendar.create_event(

        "Coding Assessment",

        "2026-10-18"

    )
