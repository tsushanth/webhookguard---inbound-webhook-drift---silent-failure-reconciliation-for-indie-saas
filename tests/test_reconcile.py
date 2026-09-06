import json
import os
import unittest

from webhookguard.models import ProcessedEvent, ProviderEvent
from webhookguard.reconcile import load_processed_events, load_provider_events, reconcile

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def _truth_event(**overrides):
    base = dict(
        id="evt_1",
        type="invoice.payment_succeeded",
        created_at="2026-08-01T00:00:00Z",
        object_id="in_1",
    )
    base.update(overrides)
    return ProviderEvent(**base)


class TestReconcileDriftTypes(unittest.TestCase):
    def test_clean_fixture_reports_no_drift(self):
        provider_events = [_truth_event()]
        processed_events = [ProcessedEvent(event_id="evt_1", processed_at="2026-08-01T00:05:00Z")]

        findings = reconcile(provider_events, processed_events)

        self.assertEqual(findings, [])

    def test_missing_event_never_processed(self):
        provider_events = [_truth_event(id="evt_missing")]
        processed_events = []

        findings = reconcile(provider_events, processed_events)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "missing")
        self.assertEqual(findings[0].event_id, "evt_missing")

    def test_duplicate_event_processed_twice(self):
        provider_events = [_truth_event(id="evt_dup")]
        processed_events = [
            ProcessedEvent(event_id="evt_dup", processed_at="2026-08-01T00:05:00Z"),
            ProcessedEvent(event_id="evt_dup", processed_at="2026-08-01T00:06:00Z"),
        ]

        findings = reconcile(provider_events, processed_events)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "duplicate")
        self.assertEqual(findings[0].event_id, "evt_dup")

    def test_late_event_outside_retry_window(self):
        provider_events = [_truth_event(id="evt_late", created_at="2026-08-01T00:00:00Z")]
        processed_events = [ProcessedEvent(event_id="evt_late", processed_at="2026-08-05T00:00:00Z")]

        findings = reconcile(provider_events, processed_events)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "late")
        self.assertEqual(findings[0].event_id, "evt_late")

    def test_processed_within_retry_window_is_not_late(self):
        provider_events = [_truth_event(id="evt_ontime", created_at="2026-08-01T00:00:00Z")]
        processed_events = [ProcessedEvent(event_id="evt_ontime", processed_at="2026-08-02T00:00:00Z")]

        findings = reconcile(provider_events, processed_events)

        self.assertEqual(findings, [])


class TestReconcileFixtureFiles(unittest.TestCase):
    def test_stripe_fixtures_report_one_of_each_drift_type(self):
        with open(os.path.join(FIXTURES_DIR, "stripe_provider_truth.json")) as f:
            provider_events = load_provider_events(json.load(f))
        with open(os.path.join(FIXTURES_DIR, "stripe_webhook_log.json")) as f:
            processed_events = load_processed_events(json.load(f))

        findings = reconcile(provider_events, processed_events)
        kinds = sorted(f.kind for f in findings)

        self.assertEqual(kinds, ["duplicate", "late", "missing"])
        self.assertEqual({f.event_id for f in findings}, {"evt_1002", "evt_1003", "evt_1004"})


if __name__ == "__main__":
    unittest.main()
