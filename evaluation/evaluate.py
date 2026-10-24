"""Evaluate stage detection and normalized dates on a locally labeled CSV."""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.timeline_builder import TimelineBuilder


def evaluate(path):
    builder = TimelineBuilder()
    expected_events = Counter()
    predicted_events = Counter()
    true_events = 0
    dates_checked = 0
    dates_correct = 0
    documents = 0

    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not row.get("text", "").strip():
                continue
            labels = json.loads(row.get("expected", "[]"))
            reference = row.get("reference_date") or None
            predictions = builder.build_timeline(row["text"], reference_date=reference)
            expected_events.update(item["Event"].strip().casefold() for item in labels)
            predicted_events.update(item["Event"].strip().casefold() for item in predictions)
            true_events += sum((Counter(item["Event"].strip().casefold() for item in labels) & Counter(item["Event"].strip().casefold() for item in predictions)).values())

            expected_by_event = defaultdict(list)
            predicted_by_event = defaultdict(list)
            for item in labels:
                expected_by_event[item["Event"].strip().casefold()].append(item["Date"])
            for item in predictions:
                predicted_by_event[item["Event"].strip().casefold()].append(item["Date"])
            for event, expected_dates in expected_by_event.items():
                predicted_dates = predicted_by_event[event]
                for index, expected_date in enumerate(expected_dates):
                    if index < len(predicted_dates):
                        dates_checked += 1
                        dates_correct += predicted_dates[index] == expected_date
            documents += 1

    precision = true_events / sum(predicted_events.values()) if predicted_events else 0.0
    recall = true_events / sum(expected_events.values()) if expected_events else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    date_accuracy = dates_correct / dates_checked if dates_checked else 0.0
    print(f"Documents evaluated: {documents}")
    print(f"Event precision: {precision:.3f}")
    print(f"Event recall:    {recall:.3f}")
    print(f"Event F1:        {f1:.3f}")
    print(f"Exact date accuracy among matched event labels: {date_accuracy:.3f} ({dates_correct}/{dates_checked})")
    if dates_checked < sum(expected_events.values()):
        print("Some labeled event mentions were not detected; their dates are excluded from date accuracy.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", help="Path to the locally labeled evaluation CSV")
    evaluate(parser.parse_args().csv_path)
