from src.google_calendar import GoogleCalendar


class CalendarGenerator:

    def __init__(self):
        self.calendar = None

    def create_calendar(self, timeline):

        created = []
        created_events = []
        failed = []
        if timeline and self.calendar is None:
            self.calendar = GoogleCalendar()
        for item in timeline:

            day, month, year = item["Date"].split("-")

            google_date = f"{year}-{month}-{day}"

            try:
                event_id = self.calendar.create_event(item["Event"], google_date)
                created.append(item["Event"])
                created_events.append({"id": event_id, "title": item["Event"], "date": item["Date"]})
            except Exception as exc:
                failed.append({"Event": item["Event"], "error": str(exc)})
        return {"created": created, "created_events": created_events, "failed": failed}
