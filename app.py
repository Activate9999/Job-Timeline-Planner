from datetime import datetime
import os
import hmac
import secrets

from flask import Flask, abort, render_template, request, session

from src.timeline_builder import TimelineBuilder
from src.calendar_generator import CalendarGenerator
from src.google_calendar import GoogleCalendar
from src.application_store import ApplicationStore
from googleapiclient.errors import HttpError

app = Flask(__name__)

timeline_builder = TimelineBuilder()
application_store = ApplicationStore(os.path.join(app.instance_path, "job_timeline.sqlite3"))
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "development-only-change-me")


@app.before_request
def csrf_protection():
    token = session.get("csrf_token")
    if request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        if not token or not hmac.compare_digest(token, submitted):
            abort(400, description="The form expired. Reload the page and try again.")
    if not token:
        session["csrf_token"] = secrets.token_urlsafe(32)


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": session.get("csrf_token", "")}


@app.route("/")
def home():
    return render_template("index.html", today=datetime.now().strftime("%Y-%m-%d"), applications_count=len(application_store.list_applications()))


@app.route("/predict", methods=["POST"])
def predict():

    text = request.form.get("job_text", "").strip()
    if not text:
        return render_template("index.html", today=datetime.now().strftime("%Y-%m-%d"), error="Paste the interview email or job text first."), 400

    reference_date = request.form.get("reference_date") or datetime.now().strftime("%Y-%m-%d")
    application_label = request.form.get("application_label", "").strip()
    timeline = timeline_builder.build_timeline(text, reference_date=reference_date)

    return render_template(
        "timeline.html",
        timeline=timeline,
        application_label=application_label,
        applications_count=len(application_store.list_applications()),
        error="No dated hiring stages were found. Try including an event and its date, or a relative date such as 'in 3 days'." if not timeline else None,
    )


@app.route("/calendar", methods=["POST"])
def calendar():

    events = request.form.getlist("event")
    dates = request.form.getlist("date")
    evidence = request.form.getlist("evidence")
    date_phrases = request.form.getlist("date_phrase")
    date_sources = request.form.getlist("date_source")
    certainties = request.form.getlist("certainty")
    application_label = request.form.get("application_label", "").strip()[:120]
    timeline = []
    review_timeline = []
    try:
        if len(events) != len(dates):
            raise ValueError("The submitted event list was incomplete. Please review it and try again.")
        for index, (event, date) in enumerate(zip(events, dates)):
            parsed = datetime.strptime(date, "%Y-%m-%d")
            event = event.strip()
            if event:
                item = {
                    "Event": event[:120], "Date": parsed.strftime("%d-%m-%Y"),
                    "Evidence": evidence[index] if index < len(evidence) else "",
                    "DatePhrase": date_phrases[index] if index < len(date_phrases) else "",
                    "DateSource": date_sources[index] if index < len(date_sources) else "",
                    "Certainty": certainties[index] if index < len(certainties) else "",
                }
                timeline.append(item)
                review_timeline.append(item)
        if not timeline:
            raise ValueError("Select at least one valid event.")
        if not application_label:
            raise ValueError("Add a company or role name so you can manage these rounds from My applications.")
        application_id = application_store.create_application(application_label, timeline)
        result = CalendarGenerator().create_calendar(timeline)
        application_store.save_created_events(application_id, result["created_events"])
    except (ValueError, OSError, RuntimeError) as exc:
        if "application_id" in locals():
            application_store.remove_application(application_id)
        return render_template("timeline.html", timeline=review_timeline, application_label=application_label, error=str(exc), applications_count=len(application_store.list_applications())), 400
    except Exception as exc:
        app.logger.exception("Google Calendar export failed")
        if "application_id" in locals():
            application_store.remove_application(application_id)
        return render_template("timeline.html", timeline=review_timeline, application_label=application_label, error="Could not connect to Google Calendar. Check credentials and try again."), 502

    return render_template("success.html", created=result["created"], failed=result["failed"], application_label=application_label, applications_count=len(application_store.list_applications()))


@app.route("/applications")
def applications():
    return render_template("applications.html", applications=application_store.list_applications(), applications_count=len(application_store.list_applications()))


@app.route("/applications/<int:application_id>/toggle", methods=["POST"])
def toggle_application(application_id):
    application = application_store.get_application(application_id)
    if not application:
        return render_template("applications.html", applications=application_store.list_applications(), error="That application could not be found."), 404
    enabled = request.form.get("enabled") == "true"
    errors = []
    try:
        calendar = GoogleCalendar()
        if enabled:
            for item in application["events"]:
                if item["status"] == "active" and item["google_event_id"]:
                    continue
                try:
                    year, month, day = item["date"].split("-")
                    event_id = calendar.create_event(item["title"], f"{year}-{month}-{day}")
                    application_store.set_event_calendar(item["id"], event_id, "active")
                except Exception as exc:
                    errors.append(f"{item['title']}: {exc}")
        else:
            for item in application["events"]:
                if item["status"] == "active" and item["google_event_id"]:
                    try:
                        calendar.delete_event(item["google_event_id"])
                        application_store.set_event_calendar(item["id"], None, "removed")
                    except HttpError as exc:
                        if exc.resp.status == 404:
                            application_store.set_event_calendar(item["id"], None, "removed")
                        else:
                            errors.append(f"{item['title']}: {exc}")
                    except Exception as exc:
                        errors.append(f"{item['title']}: {exc}")
                elif item["status"] != "removed":
                    application_store.set_event_status(item["id"], "removed")
        current = application_store.get_application(application_id)
        any_active = any(item["status"] == "active" for item in current["events"])
        application_store.set_application_active(application_id, any_active if errors else enabled)
    except Exception as exc:
        app.logger.exception("Application calendar toggle failed")
        errors.append(str(exc))
    current_applications = application_store.list_applications()
    return render_template("applications.html", applications=current_applications,
        error=("Some calendar events could not be updated: " + "; ".join(errors)) if errors else None,
        notice=None if errors else (f"Calendar rounds for {application['label']} were {'restored' if enabled else 'removed'}.") ,
        applications_count=len(current_applications)), 502 if errors else 200


if __name__ == "__main__":
    app.run(debug=True)
