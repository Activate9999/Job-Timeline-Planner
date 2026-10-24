# Job Timeline Predictor

A Flask application that finds common hiring stages and associated dates in pasted interview emails or job updates. Review and edit the extracted events before optionally adding them as all-day events to Google Calendar.

## Run locally

1. Use Python 3.10 or newer and create/activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. For Calendar export, create a Google Cloud OAuth desktop-app client with the Google Calendar API enabled. Save its downloaded client secret as `credentials/credentials.json`. The first export opens the Google sign-in flow and saves a token at `credentials/token.json`.
4. Start the Flask app with `python app.py` and open `http://127.0.0.1:5000`.

Calendar credentials are only needed for the export feature; timeline extraction works without them. Keep both credential files private and out of source control. Set `FLASK_SECRET_KEY` to a random value when running beyond local development. Do not expose Flask's debug server to the public internet.

## How extraction works

The current application uses a rule-based event vocabulary and dateparser. It supports common hiring stage names, explicit dates, and relative dates such as "tomorrow," "next week," or "in 3 days." Relative expressions use the reference date on the input page and then the most recently detected date. The review page includes the source clause, date phrase, and whether the date was found or inferred. It flags inferred dates, rescheduling, and clauses containing multiple dates. Events without a detected date are omitted. The parser is still a baseline: complex cross-sentence references and unusual negation can be misread, so check every result before exporting.

## Application tracker

When exporting a timeline, enter a company or role label. The **My applications** page groups the calendar rounds by that label. Its switch removes the events created for that application from the primary Google Calendar; switching it on again restores those same rounds. The tracker stores labels, event dates, and Google Calendar event IDs in `instance/job_timeline.sqlite3`. It does not store the pasted email or job description. The local database, OAuth token, and OAuth client file are excluded by `.gitignore`.

The `src/event_extractor.py` and `src/time_extractor.py` scripts can prepare event and TIMEX3 tables from the included TimeML corpora. Those general news corpora are not labeled hiring emails, and the current web predictor does not train on their CSV outputs. To measure the current baseline, build a small consented, anonymized sample of hiring emails and label each document's expected events and normalized dates. Do not put names, email addresses, phone numbers, company secrets, or unredacted private messages in a shared repository. Keep examples from the same sender/template together when creating any future train/test split to reduce leakage.

Copy `evaluation/labels_template.csv` to a private location, then fill `document_id`, `reference_date` (`YYYY-MM-DD`), `text` (anonymized email), and `expected` (a JSON list such as `[{"Event":"Coding Assessment","Date":"18-10-2026"}]`). Run `python evaluation/evaluate.py path/to/your_private_labels.csv`. The script prints event precision, recall, F1, and exact date accuracy for detected events; it does not print message text. This creates a repeatable baseline before changing the extraction rules.

## Main components

- `app.py`: Flask routes and form validation.
- `src/timeline_builder.py`: rule-based stage and date extraction.
- `src/calendar_generator.py`, `src/google_calendar.py`: Google Calendar export.
- `src/event_extractor.py`, `src/time_extractor.py`: TimeML dataset preparation scripts.
- `data/processed/`: generated CSVs from the corpus extraction scripts.
