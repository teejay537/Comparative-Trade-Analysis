"""Scoring logic for tariff-negotiation strategy."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ScoreWeights:
    """Weights used by the composite scoring formulas.

    The defaults intentionally give meaningful weight to trade flows, but keep tariffs,
    productive capacity, and strategic importance visible in the result.
    """

    tariff_weight: float = 0.30
    trade_flow_weight: float = 0.30
    domestic_capacity_weight: float = 0.20
    strategic_importance_weight: float = 0.20
    concession_partner_interest_weight: float = 0.55
    concession_low_sensitivity_weight: float = 0.45

    def validate(self) -> None:
        offensive_total = (
            self.tariff_weight
            + self.trade_flow_weight
            + self.domestic_capacity_weight
            + self.strategic_importance_weight
        )
        concession_total = (
            self.concession_partner_interest_weight
            + self.concession_low_sensitivity_weight
        )

        if not np.isclose(offensive_total, 1.0):
            raise ValueError("Main score weights must sum to 1.0.")
        if not np.isclose(concession_total, 1.0):
            raise ValueError("Concession score weights must sum to 1.0.")


def min_max_scale(series: pd.Series) -> pd.Series:
    """Scale a numeric series to 0-1, with a safe fallback for constant values."""
    numeric = pd.to_numeric(series, errors="coerce").fillna(0).astype(float)
    minimum = numeric.min()
    maximum = numeric.max()
    if np.isclose(maximum, minimum):
        return pd.Series(0.0, index=series.index)
    return (numeric - minimum) / (maximum - minimum)


def score_product_lines(df: pd.DataFrame, weights: ScoreWeights | None = None) -> pd.DataFrame:
    """Calculate product-level strategy scores from a merged model dataset."""
    weights = weights or ScoreWeights()
    weights.validate()

    scored = df.copy()

    # Normalize core values.
    # Tariff rates are min-max scaled rather than divided by 100 because, in many
    # real negotiations, a 20-30% tariff is already a major barrier. Relative
    # tariff ranking across the product schedule is usually more informative
    # than treating 30% as only 0.30 of a theoretical 100% maximum.
    scored["a_tariff_norm"] = min_max_scale(scored["a_tariff_rate"])
    scored["b_tariff_norm"] = min_max_scale(scored["b_tariff_rate"])
    scored["a_capacity_norm"] = scored["a_domestic_capacity_score"] / 100
    scored["b_capacity_norm"] = scored["b_domestic_capacity_score"] / 100
    scored["a_strategic_norm"] = scored["a_strategic_importance_score"] / 100
    scored["b_strategic_norm"] = scored["b_strategic_importance_score"] / 100
    scored["exports_a_to_b_norm"] = min_max_scale(scored["exports_a_to_b"])
    scored["exports_b_to_a_norm"] = min_max_scale(scored["exports_b_to_a"])

    # Country A wants Country B to reduce tariffs where B's tariff is high,
    # Country A has supply capacity, the product matters strategically to A,
    # and exports from A to B are already commercially meaningful.
    scored["a_offensive_priority"] = 100 * (
        weights.tariff_weight * scored["b_tariff_norm"]
        + weights.trade_flow_weight * scored["exports_a_to_b_norm"]
        + weights.domestic_capacity_weight * scored["a_capacity_norm"]
        + weights.strategic_importance_weight * scored["a_strategic_norm"]
    )

    # Country A should be cautious reducing its own tariff where A's tariff is high,
    # domestic productive capacity is strong, strategic importance is high,
    # and Country B already sells into Country A's market.
    scored["a_defensive_sensitivity"] = 100 * (
        weights.tariff_weight * scored["a_tariff_norm"]
        + weights.trade_flow_weight * scored["exports_b_to_a_norm"]
        + weights.domestic_capacity_weight * scored["a_capacity_norm"]
        + weights.strategic_importance_weight * scored["a_strategic_norm"]
    )

    # Symmetric view: where Country B is likely to demand market access from A.
    scored["b_offensive_priority"] = 100 * (
        weights.tariff_weight * scored["a_tariff_norm"]
        + weights.trade_flow_weight * scored["exports_b_to_a_norm"]
        + weights.domestic_capacity_weight * scored["b_capacity_norm"]
        + weights.strategic_importance_weight * scored["b_strategic_norm"]
    )

    # A can treat a product as a possible concession if B wants access, but A's own
    # defensive sensitivity is not high.
    scored["a_concession_value"] = (
        weights.concession_partner_interest_weight * scored["b_offensive_priority"]
        + weights.concession_low_sensitivity_weight * (100 - scored["a_defensive_sensitivity"])
    )

    scored["a_net_negotiating_value"] = (
        scored["a_offensive_priority"] - scored["a_defensive_sensitivity"]
    )

    score_cols = [
        "a_offensive_priority",
        "a_defensive_sensitivity",
        "b_offensive_priority",
        "a_concession_value",
        "a_net_negotiating_value",
    ]
    scored[score_cols] = scored[score_cols].round(2)

    scored["recommended_a_strategy"] = scored.apply(classify_a_strategy, axis=1)
    scored["analyst_rationale"] = scored.apply(make_rationale, axis=1)

    return scored


def classify_a_strategy(row: pd.Series) -> str:
    """Translate scores into a negotiation category for Country A."""
    offensive = row["a_offensive_priority"]
    defensive = row["a_defensive_sensitivity"]
    partner_interest = row["b_offensive_priority"]
    concession = row["a_concession_value"]

    if offensive >= 70 and defensive >= 70:
        return "High-value reciprocal tradeoff"
    if offensive >= 70:
        return "Priority ask from Country B"
    if defensive >= 60 and offensive < 55:
        return "Protect / red-line item"
    if concession >= 52 and defensive < 50 and partner_interest >= 50:
        return "Possible concession / bargaining chip"
    if offensive >= 55 or partner_interest >= 55 or defensive >= 55:
        return "Balanced negotiation item"
    return "Low-priority or monitor"


def make_rationale(row: pd.Series) -> str:
    """Create a concise explanation for the recommended strategy."""
    reasons: list[str] = []

    if row["b_tariff_rate"] >= 15:
        reasons.append("partner tariff is high")
    if row["a_tariff_rate"] >= 15:
        reasons.append("home tariff is high")
    if row["a_domestic_capacity_score"] >= 70:
        reasons.append("home productive capacity is strong")
    if row["a_strategic_importance_score"] >= 80:
        reasons.append("home strategic importance is high")
    if row["exports_a_to_b"] > row["exports_b_to_a"]:
        reasons.append("A exports more to B than B exports to A")
    elif row["exports_b_to_a"] > row["exports_a_to_b"]:
        reasons.append("B exports more to A than A exports to B")

    if not reasons:
        reasons.append("scores are moderate across tariff, trade, capacity, and strategy factors")

    return "; ".join(reasons)
