"""Core diff engine: provider source-of-truth vs. webhook processing log.

This is the whole point of WebhookGuard. Everything else (CLI, report
formatting) exists to expose this comparison.
"""

from collections import Counter
from datetime import datetime, timedelta

from webhookguard.models import DriftFinding, ProcessedEvent, ProviderEvent

# Most providers (Stripe included) give up retrying a failed webhook
# delivery after roughly 3 days. An event processed later than that was
# likely already written off / handled manually.
RETRY_WINDOW = timedelta(days=3)


def _parse_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_provider_events(records):
    return [
        ProviderEvent(
            id=r["id"],
            type=r["type"],
            created_at=r["created_at"],
            object_id=r["object_id"],
        )
        for r in records
    ]


def load_processed_events(records):
    return [
        ProcessedEvent(event_id=r["event_id"], processed_at=r["processed_at"])
        for r in records
    ]


def reconcile(provider_events, processed_events, retry_window=RETRY_WINDOW):
    """Diff provider truth against the processed log and classify drift.

    Returns a list of DriftFinding, sorted by event id for stable output.
    """
    processed_by_id = Counter(pe.event_id for pe in processed_events)
    first_processed_at = {}
    for pe in processed_events:
        if pe.event_id not in first_processed_at:
            first_processed_at[pe.event_id] = pe.processed_at

    findings = []
    for event in provider_events:
        occurrences = processed_by_id.get(event.id, 0)

        if occurrences == 0:
            findings.append(
                DriftFinding(
                    kind="missing",
                    event_id=event.id,
                    detail=(
                        f"{event.type} for {event.object_id} exists in provider "
                        f"truth (created {event.created_at}) but was never "
                        "processed by the webhook handler"
                    ),
                )
            )
            continue

        if occurrences > 1:
            findings.append(
                DriftFinding(
                    kind="duplicate",
                    event_id=event.id,
                    detail=(
                        f"{event.type} for {event.object_id} was processed "
                        f"{occurrences} times (expected 1) — likely a retry "
                        "applied twice"
                    ),
                )
            )

        processed_at = _parse_timestamp(first_processed_at[event.id])
        created_at = _parse_timestamp(event.created_at)
        if processed_at - created_at > retry_window:
            findings.append(
                DriftFinding(
                    kind="late",
                    event_id=event.id,
                    detail=(
                        f"{event.type} for {event.object_id} was processed "
                        f"{processed_at - created_at} after creation, "
                        f"outside the {retry_window} retry window"
                    ),
                )
            )

    findings.sort(key=lambda f: (f.event_id, f.kind))
    return findings
