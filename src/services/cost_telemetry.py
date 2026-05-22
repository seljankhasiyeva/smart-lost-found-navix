from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


MODEL_PRICING_PER_1K_TOKENS: dict[str, float] = {
    "text-embedding-3-small": 0.00002,
    "claude-sonnet-4-6": 0.003,
    "gpt-4o-mini": 0.00015,
    "offline": 0.0,
}


def estimate_tokens(text: str) -> int:
    """
    Estimate token count.

    This is approximate:
    1 token ≈ 4 characters.
    """

    if not text:
        return 1

    return max(1, len(text) // 4)


def estimate_cost(model: str, tokens: int) -> float:
    """
    Estimate cost for a model based on token count.
    """

    price_per_1k = MODEL_PRICING_PER_1K_TOKENS.get(model, 0.0)
    return (tokens / 1000) * price_per_1k


@dataclass
class CostEvent:
    operation: str
    provider: str
    model: str
    tokens: int
    estimated_cost: float


@dataclass
class CostTelemetry:
    """
    In-memory cost tracker.

    Tracks token counts and estimated cost per provider/model.
    """

    events: list[CostEvent] = field(default_factory=list)

    def record(
        self,
        operation: str,
        provider: str,
        model: str,
        text: str,
    ) -> CostEvent:
        tokens = estimate_tokens(text)
        cost = estimate_cost(model, tokens)

        event = CostEvent(
            operation=operation,
            provider=provider,
            model=model,
            tokens=tokens,
            estimated_cost=cost,
        )

        self.events.append(event)

        return event

    def total_tokens(self) -> int:
        return sum(event.tokens for event in self.events)

    def total_cost(self) -> float:
        return sum(event.estimated_cost for event in self.events)

    def summary_by_provider(self) -> Dict[str, dict]:
        summary: Dict[str, dict] = {}

        for event in self.events:
            if event.provider not in summary:
                summary[event.provider] = {
                    "tokens": 0,
                    "estimated_cost": 0.0,
                    "calls": 0,
                }

            summary[event.provider]["tokens"] += event.tokens
            summary[event.provider]["estimated_cost"] += event.estimated_cost
            summary[event.provider]["calls"] += 1

        return summary


global_cost_telemetry = CostTelemetry()