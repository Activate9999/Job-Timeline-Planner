from __future__ import print_function

import os.path
from pathlib import Path

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendar:

    def __init__(self):

        self.service = self.authenticate()

    def authenticate(self):

        creds = None

        project_root = Path(__file__).resolve().parent.parent
        token_path = project_root / "credentials" / "token.json"
        credentials_path = project_root / "credentials" / "credentials.json"

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
                    creds = self._authorize(credentials_path)

            else:

                if not os.path.exists(credentials_path):
                    raise RuntimeError(
                        "Google Calendar is not configured. Add credentials/credentials.json from Google Cloud Console."
                    )

                creds = self._authorize(credentials_path)

            with open(token_path, "w") as token:

                token.write(creds.to_json())

        service = build("calendar", "v3", credentials=creds)

        return service

    @staticmethod
    def _authorize(credentials_path):
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        return flow.run_local_server(port=0, open_browser=True)

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
