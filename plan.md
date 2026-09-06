# WebhookGuard — Local MVP Scaffold Plan

## Goal of this MVP

Prove the *reconciliation* idea, not build a webhook receiver. The core value
isn't "we capture webhook traffic" (ngrok/Webhook.site/RequestBin already do
that) — it's "we diff what a provider says actually happened against what
your handler actually processed, and surface drift." A local demo should
show that diff engine working end-to-end on realistic data, with zero
infrastructure.

## Stack choice

**Python 3, standard library only.** No pip installs, no framework, no
runtime service.

Why this over Node/TS or Go:
- The core logic is set comparison + simple time-window rules over JSON —
  no need for a type system, a compiler step, or a binary build.
- `argparse`, `json`, `sqlite3`, `datetime`, and `unittest` cover everything
  needed (CLI parsing, data loading, optional persistence, date math,
  tests) with zero dependencies to install, which keeps "clone and run" to
  one command.
- A single-file-first CLI keeps the reconciliation logic inspectable in one
  sitting — appropriate for an idea-validation scaffold, not a product build.

## What this MVP does NOT need (and why)

- **No real Stripe/Shopify/Twilio/RevenueCat API calls.** The core claim to
  prove is "reconciliation against source-of-truth catches drift that
  webhook-only logging misses." That's provable with realistic *mocked*
  provider API responses (JSON fixtures shaped like real API payloads).
  Live API calls would require API keys, network access, and account setup
  — none of which change whether the diff logic is sound.
- **No polling scheduler / cron / background daemon.** "Periodically polls"
  is a deployment concern. The MVP runs reconciliation on demand via a CLI
  command; the diff logic is identical whether triggered by cron or by
  hand.
- **No database server.** Fixtures are flat JSON files representing (a) the
  provider's source-of-truth event list and (b) the webhook handler's
  processing log. A local SQLite file is used only if useful for exploring
  results interactively — not required for the demo to work.
- **No auth, accounts, billing, or multi-tenant anything.** Single local
  user, single local run.
- **No hosting/deploy.** Runs from the checked-out directory only.
- **No web UI/dashboard.** Output is a CLI report (table + summary counts).
  A dashboard is a presentation layer over the same diff engine — doesn't
  change whether reconciliation works.
- **Only one provider's fixture shape (Stripe) for the initial demo.** The
  adapter/schema is written provider-agnostically (generic `ProviderEvent`
  shape: id, type, created_at, object_id), so Shopify/Twilio/RevenueCat
  would plug in as additional fixture sets later — but only Stripe fixtures
  are needed to prove the core value now.

## Drift types demoed (the named failure modes from the sources)

1. **Missing** — event exists in provider's source-of-truth but never
   appears in the webhook handler's processed log (the 500-spike / expired
   retry-window case).
2. **Duplicate** — an event ID appears more than once in the processed log
   (the double-applied retry case).
3. **Late** — event was eventually processed, but outside the provider's
   retry window (e.g., processed >3 days after `created_at`), so it may
   have already been given up on / reconciled manually.

## File/directory layout

```
webhookguard.py                    # CLI entrypoint (argparse: `reconcile` command)
webhookguard/
  __init__.py
  models.py                        # ProviderEvent, ProcessedEvent, DriftFinding dataclasses
  reconcile.py                     # core diff logic: build sets, classify drift
  report.py                        # render findings as a CLI table + summary
fixtures/
  stripe_provider_truth.json       # mock "what actually happened" per Stripe API
  stripe_webhook_log.json          # mock "what our handler actually processed"
tests/
  test_reconcile.py                # unittest cases: missing/duplicate/late + happy path
plan.md
```

## Verification plan

- **Automated:** `python -m unittest discover tests` — covers each drift
  type in isolation (a fixture pair engineered to contain exactly one kind
  of drift) plus a clean-fixture case that should report zero findings.
- **Manual run-through:**
  1. `python webhookguard.py reconcile --provider stripe --fixtures fixtures/`
  2. Confirm the output lists the specific injected drift cases (one
     missing, one duplicate, one late event) with event IDs and a summary
     line (e.g. "3 drift findings: 1 missing, 1 duplicate, 1 late").
  3. Edit `fixtures/stripe_webhook_log.json` to remove one of the
     discrepancies and re-run, confirming the finding disappears — proving
     the diff is actually driven by the data, not hardcoded.
