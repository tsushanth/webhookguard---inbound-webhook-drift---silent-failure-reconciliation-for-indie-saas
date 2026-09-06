# WebhookGuard

A local proof-of-concept for the core idea behind WebhookGuard: **reconciling
what a provider's source-of-truth API says actually happened against what
your webhook handler actually processed**, and surfacing the drift.

Existing tools (ngrok, Webhook.site, RequestBin, WebhookBeam) capture or
notify on webhook traffic. None of them catch the failure modes that
actually cost money: the event missed during a 500 spike, the retry window
that expired over a holiday, the retry that got double-applied. Those only
show up when you diff deliveries against the provider's own record of
events — which is what this reconciliation engine does.

This is a scaffold to prove the diff logic works end-to-end on realistic
data, not a hosted product. It doesn't call any real provider API, run a
scheduler, or serve a UI — see `plan.md` for what's deliberately out of
scope and why.

## What it does

Given two JSON files —

1. a provider's **source-of-truth** event list (what actually happened), and
2. your webhook handler's **processed log** (what you actually handled) —

it classifies drift into three named failure modes:

- **Missing** — the event exists at the provider but was never processed
  (500-spike / expired retry window).
- **Duplicate** — the event was processed more than once (double-applied
  retry).
- **Late** — the event was processed, but more than 3 days after it was
  created, i.e. outside the provider's typical retry window.

## Requirements

Python 3.9+, standard library only. No `pip install` needed.

## Run it

```bash
python webhookguard.py reconcile --provider stripe --fixtures fixtures/
```

Expected output against the bundled fixtures (`fixtures/stripe_provider_truth.json`
and `fixtures/stripe_webhook_log.json`, which have one of each drift type
deliberately injected):

```
KIND       EVENT ID             DETAIL
--------------------------------------
MISSING    evt_1002             invoice.payment_succeeded for in_B2 exists in provider truth ...
DUPLICATE  evt_1003             charge.succeeded for ch_C3 was processed 2 times (expected 1) ...
LATE       evt_1004             customer.subscription.updated for sub_D4 was processed 3 days, 1:00:00 after creation ...

3 drift findings: 1 missing, 1 duplicate, 1 late
```

The command exits with status `1` when drift is found and `0` when the log
matches the provider's truth — so it can be wired into a cron job or CI
check later without any code changes.

To confirm the diff is actually driven by the fixture data (not hardcoded),
edit `fixtures/stripe_webhook_log.json` to add a processed entry for
`evt_1002` and re-run — the "missing" finding disappears.

## Run the tests

```bash
python -m unittest discover tests
```

Covers each drift type in isolation, a clean-fixture case with zero
findings, and an integration test against the bundled fixture files.

## Layout

```
webhookguard.py           CLI entrypoint (argparse: `reconcile` command)
webhookguard/
  models.py                ProviderEvent, ProcessedEvent, DriftFinding
  reconcile.py              core diff logic: build sets, classify drift
  report.py                 renders findings as a CLI table + summary
fixtures/
  stripe_provider_truth.json   mock "what actually happened" per Stripe's API
  stripe_webhook_log.json      mock "what our handler actually processed"
tests/
  test_reconcile.py         unit + integration tests
```

`ProviderEvent` is provider-agnostic (`id`, `type`, `created_at`,
`object_id`), so Shopify/Twilio/RevenueCat fixtures could plug into the same
`--provider <name>` convention later — only Stripe fixtures exist today.

See `plan.md` for the full scope rationale.
