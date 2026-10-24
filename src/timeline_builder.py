import re
from datetime import datetime, timedelta

import dateparser
from dateparser.search import search_dates


class TimelineBuilder:
    """Rule-based hiring event and date extractor with evidence for review."""

    EVENT_PATTERNS = [
        ("Resume Screening", r"\b(?:resume|cv)\s+(?:screening|shortlisting)\b"),
        ("Application", r"\bapplication\s+(?:submitted|received|date)\b|\bapply(?:ing)?\s+by\b"),
        ("Shortlisted", r"\bshortlist(?:ed|ing)?\b"),
        ("Online Assessment", r"\bonline\s+assessment\b"),
        ("Aptitude Test", r"\baptitude\s+(?:test|assessment)\b"),
        ("Coding Assessment", r"\bcoding\s+assessment\b"),
        ("Coding Test", r"\bcoding\s+test\b"),
        ("Hackathon", r"\bhackathon\b"),
        ("Technical Round 1", r"\btechnical\s+(?:round|interview)\s*(?:1|one|i)\b"),
        ("Technical Round 2", r"\btechnical\s+(?:round|interview)\s*(?:2|two|ii)\b"),
        ("Technical Interview", r"\btechnical\s+interview\b|\btechnical\s+round\b"),
        ("Machine Coding", r"\bmachine\s+coding\b"),
        ("System Design", r"\bsystem\s+design\b"),
        ("Managerial Interview", r"\bmanagerial\s+(?:round|interview)\b|\bmanager\s+interview\b"),
        ("HR Discussion", r"\bhr\s+discussion\b"),
        ("HR Interview", r"\bhr\s+(?:round|interview)\b|\bhuman\s+resources\s+interview\b"),
        ("Document Verification", r"\bdocument\s+verification\b"),
        ("Background Verification", r"\bbackground\s+(?:check|verification)\b"),
        ("Medical Test", r"\bmedical\s+(?:test|examination)\b"),
        ("Offer Acceptance", r"\boffer\s+acceptance\b|\baccept(?:ing)?\s+the\s+offer\b"),
        ("Offer", r"\bjob\s+offer\b|\boffer\s+(?:letter|released|extended)\b"),
        ("Internship", r"\binternship\s+(?:start|begins|joining)\b"),
        ("Joining", r"\bjoining\s+(?:date|day|on)\b|\bjoin(?:ing)?\s+the\s+(?:company|team)\b"),
    ]
    CANCELLED = re.compile(r"(?<!\bnot\s)\b(?:cancelled|canceled)\b|\b(?:will not|won't)\s+(?:take place|be held|go ahead)\b|\b(?:no longer scheduled|not scheduled)\b", re.I)
    NEGATED_EVENT = re.compile(r"\b(?:not|never)\s+(?:have\s+)?(?:a\s+)?(?:coding assessment|coding test|online assessment|technical interview|technical round|hr interview|interview)\b", re.I)
    DATE_TOKEN = re.compile(
        r"\b(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:\s+\d{4})?|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?|today|tomorrow|next\s+(?:week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|in\s+\w+\s+(?:days?|weeks?)|after\s+\w+\s+(?:days?|weeks?))\b",
        re.I,
    )

    def build_timeline(self, text, reference_date=None):
        if not isinstance(text, str):
            return []
        base = reference_date or datetime.now()
        if isinstance(base, str):
            base = dateparser.parse(base)
        if base is None:
            base = datetime.now()

        timeline = []
        previous_date = None
        # Keep clauses together so punctuation in numeric dates does not split them.
        clauses = [part.strip() for part in re.split(r"[\n\r;]+|(?<=[.!?])\s+|\s+(?:but|however)\s+", text, flags=re.I) if part.strip()]
        for clause in clauses:
            # Ignore negated/cancelled mentions. A rescheduled clause remains visible
            # but is explicitly flagged for review below.
            if self.CANCELLED.search(clause) or self.NEGATED_EVENT.search(clause):
                continue
            mentions = self._find_events(clause)
            if not mentions:
                continue

            date_mentions = self._find_dates(clause, previous_date or base)
            if not date_mentions:
                continue
            rescheduled = bool(re.search(r"\b(?:rescheduled|postponed|moved)\b", clause, re.I))
            for event, event_start, event_end in mentions:
                selected = max(date_mentions, key=lambda item: item[0]) if rescheduled else self._closest_date(event_start, event_end, date_mentions)
                date, phrase, date_start = selected
                relative = bool(re.search(r"\b(?:in|after|tomorrow|today|next)\b", phrase, re.I))
                caution = rescheduled or len(date_mentions) > 1
                timeline.append({
                    "Event": event,
                    "Date": date.strftime("%d-%m-%Y"),
                    "Evidence": clause,
                    "DatePhrase": phrase,
                    "DateSource": "Inferred from reference date" if relative and previous_date is None else ("Inferred from previous event" if relative else "Found in text"),
                    "Certainty": "Review: rescheduled or multiple dates" if caution else ("Review: inferred date" if relative else "Found in text"),
                    "NeedsReview": caution or relative,
                })
            # A date in a multi-event clause can reasonably apply to all its events.
            # Carry the latest relevant date forward for subsequent relative phrases.
            previous_date = max(item[0] for item in date_mentions)
        return timeline

    def _find_events(self, clause):
        found = []
        for event, pattern in self.EVENT_PATTERNS:
            for match in re.finditer(pattern, clause, re.I):
                found.append((event, match.start(), match.end()))
        # Drop generic matches covered by a more specific event at the same span.
        found.sort(key=lambda item: (item[1], -(item[2] - item[1])))
        result = []
        for item in found:
            if any(item[1] >= old[1] and item[2] <= old[2] for old in result):
                continue
            result.append(item)
        return result

    @classmethod
    def _find_dates(cls, clause, relative_base):
        # Ignore round numerals so "Technical round 2" is not treated as a date.
        date_text = re.sub(r"\b(?:technical\s+)?(?:round|interview)\s*(?:1|2|one|two|i|ii)\b", " ", clause, flags=re.I)
        parsed = search_dates(date_text, settings={
            "RELATIVE_BASE": relative_base,
            "PREFER_DATES_FROM": "future",
            "DATE_ORDER": "DMY",
            "STRICT_PARSING": True,
        }) or []
        results = []
        for phrase, date in parsed:
            token = cls.DATE_TOKEN.search(phrase)
            if not token:
                continue
            start = clause.lower().find(phrase.lower())
            if start < 0:
                start = clause.lower().find(token.group().lower())
            phrase = token.group()
            # A date explicitly tied to an unrelated deadline should not be
            # attached to another hiring stage in the same clause.
            left_context = clause[max(0, start - 35):start]
            if re.search(r"\b(?:application|submission|reply|respond|registration)\s+(?:deadline|due date)\b|\bdeadline\s+(?:to|for)\s+(?:apply|submit|register)\b", left_context, re.I):
                continue
            results.append((date, phrase, start))
        if not results:
            # dateparser may not recognize spelled-out offsets in all versions.
            words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
            match = re.search(r"\b(?:after|in)\s+(\d+|" + "|".join(words) + r")\s+(days?|weeks?)\b", clause, re.I)
            if match:
                amount = int(match.group(1)) if match.group(1).isdigit() else words[match.group(1).lower()]
                date = relative_base + (timedelta(weeks=amount) if match.group(2).lower().startswith("week") else timedelta(days=amount))
                results.append((date, match.group(), match.start()))
        return results

    @staticmethod
    def _closest_date(event_start, event_end, date_mentions):
        if len(date_mentions) == 1:
            return date_mentions[0]
        return min(date_mentions, key=lambda item: min(abs(item[2] - event_end), abs(item[2] - event_start)))
