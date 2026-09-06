"""Data shapes for reconciliation: provider-agnostic on purpose.

A ProviderEvent is "what actually happened" per the provider's
source-of-truth API. A ProcessedEvent is "what our webhook handler
actually did" with an incoming delivery. DriftFinding is the output of
diffing the two.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderEvent:
    id: str
    type: str
    created_at: str  # ISO 8601 timestamp
    object_id: str


@dataclass(frozen=True)
class ProcessedEvent:
    event_id: str
    processed_at: str  # ISO 8601 timestamp


@dataclass(frozen=True)
class DriftFinding:
    kind: str  # "missing" | "duplicate" | "late"
    event_id: str
    detail: str
