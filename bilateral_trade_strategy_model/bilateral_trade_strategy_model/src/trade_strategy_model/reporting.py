"""Plain-English report generation for the trade strategy model."""

from __future__ import annotations

import pandas as pd


def _markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 8) -> str:
    """Return a small markdown table without requiring tabulate."""
    if df.empty:
        return "No records."

    table = df[columns].head(limit).copy()
    lines = []
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in table.iterrows():
        values = [str(row[col]) for col in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_markdown_report(
    scores: pd.DataFrame,
    packages: pd.DataFrame,
    country_a_name: str,
    country_b_name: str,
) -> str:
    """Build a markdown report summarizing the negotiation strategy."""
    priority_asks = scores[
        scores["recommended_a_strategy"].isin(
            ["Priority ask from Country B", "High-value reciprocal tradeoff"]
        )
    ].sort_values("a_offensive_priority", ascending=False)

    red_lines = scores[
        scores["recommended_a_strategy"].eq("Protect / red-line item")
    ].sort_values("a_defensive_sensitivity", ascending=False)

    concessions = scores[
        scores["recommended_a_strategy"].eq("Possible concession / bargaining chip")
    ].sort_values("a_concession_value", ascending=False)

    top_net = scores.sort_values("a_net_negotiating_value", ascending=False)

    strategy_counts = scores["recommended_a_strategy"].value_counts().reset_index()
    strategy_counts.columns = ["strategy", "product_count"]

    report = f"""# Bilateral Goods Trade Negotiation Report

## Negotiation perspective

This report evaluates tariff-negotiation priorities from the perspective of **{country_a_name}** in a negotiation with **{country_b_name}**.

The model combines four evidence categories: tariff levels, bilateral trade flows, domestic productive capacity, and strategic importance. Scores are scaled from 0 to 100, where higher scores indicate greater priority or sensitivity.

## Strategy category summary

{_markdown_table(strategy_counts, ["strategy", "product_count"], limit=20)}

## Highest-priority asks for {country_a_name}

These products have the strongest case for asking {country_b_name} to reduce tariffs.

{_markdown_table(priority_asks, ["hs_code", "product_description", "b_tariff_rate", "exports_a_to_b", "a_offensive_priority", "recommended_a_strategy"], limit=10)}

## Products to protect or treat cautiously

These items have higher domestic sensitivity for {country_a_name}. They may require exclusions, phase-downs, quota treatment, safeguards, or a slower concession schedule.

{_markdown_table(red_lines, ["hs_code", "product_description", "a_tariff_rate", "exports_b_to_a", "a_defensive_sensitivity", "analyst_rationale"], limit=10)}

## Possible concessions or bargaining chips for {country_a_name}

These items may be useful as concessions because {country_b_name} is likely to value access, while {country_a_name}'s defensive sensitivity is comparatively lower.

{_markdown_table(concessions, ["hs_code", "product_description", "a_tariff_rate", "b_offensive_priority", "a_concession_value", "recommended_a_strategy"], limit=10)}

## Best net negotiating-value items for {country_a_name}

These products have the largest gap between {country_a_name}'s offensive interest and domestic defensive sensitivity.

{_markdown_table(top_net, ["hs_code", "product_description", "a_offensive_priority", "a_defensive_sensitivity", "a_net_negotiating_value", "analyst_rationale"], limit=10)}

## Suggested ask-for-concession packages

{_markdown_table(packages, ["a_ask_hs_code", "a_ask_product", "a_ask_score", "a_possible_concession_hs_code", "a_possible_concession_product", "concession_sensitivity", "package_balance_score"], limit=10)}

## Practical use in negotiations

Use the product scores as a first-pass triage tool. The strongest candidates for opening demands are high offensive-priority items with clear export interest and partner tariff barriers. Products with high defensive sensitivity should be handled through carve-outs, staging, longer implementation periods, safeguard mechanisms, or reciprocal concessions. Possible concession items should be reviewed for legal feasibility, sector-specific policy constraints, and stakeholder risk before being offered.
"""
    return report
