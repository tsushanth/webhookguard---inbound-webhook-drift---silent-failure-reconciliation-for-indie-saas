#!/usr/bin/env python3
"""WebhookGuard CLI: reconcile provider source-of-truth vs. webhook processing log.

Usage:
    python webhookguard.py reconcile --provider stripe --fixtures fixtures/
"""

import argparse
import json
import os
import sys

from webhookguard.reconcile import load_processed_events, load_provider_events, reconcile
from webhookguard.report import render


def _load_json(path):
    with open(path) as f:
        return json.load(f)


def cmd_reconcile(args):
    truth_path = os.path.join(args.fixtures, f"{args.provider}_provider_truth.json")
    log_path = os.path.join(args.fixtures, f"{args.provider}_webhook_log.json")

    provider_events = load_provider_events(_load_json(truth_path))
    processed_events = load_processed_events(_load_json(log_path))

    findings = reconcile(provider_events, processed_events)
    print(render(findings, args.provider))
    return 1 if findings else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="webhookguard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reconcile_parser = subparsers.add_parser(
        "reconcile", help="diff provider source-of-truth against the webhook processing log"
    )
    reconcile_parser.add_argument("--provider", required=True, help="provider name, e.g. 'stripe'")
    reconcile_parser.add_argument(
        "--fixtures", required=True, help="directory containing '<provider>_provider_truth.json' and '<provider>_webhook_log.json'"
    )
    reconcile_parser.set_defaults(func=cmd_reconcile)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
