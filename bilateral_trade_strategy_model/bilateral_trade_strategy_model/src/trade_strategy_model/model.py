"""Core decision model for bilateral goods tariff negotiations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .io import load_inputs, write_outputs
from .reporting import build_markdown_report
from .scoring import ScoreWeights, score_product_lines


@dataclass
class TradeStrategyModel:
    """Evaluate bilateral tariff-negotiation priorities from Country A's perspective."""

    country_a_name: str = "Country A"
    country_b_name: str = "Country B"
    weights: ScoreWeights | None = None

    def prepare_model_data(
        self,
        country_a_tariffs: pd.DataFrame,
        country_b_tariffs: pd.DataFrame,
        trade_flows: pd.DataFrame,
    ) -> pd.DataFrame:
        """Merge tariff and trade-flow data into a single product-level dataset."""
        a = country_a_tariffs.rename(
            columns={
                "tariff_rate": "a_tariff_rate",
                "domestic_capacity_score": "a_domestic_capacity_score",
                "strategic_importance_score": "a_strategic_importance_score",
                "notes": "a_notes",
                "sector": "a_sector",
            }
        )

        b = country_b_tariffs.rename(
            columns={
                "tariff_rate": "b_tariff_rate",
                "domestic_capacity_score": "b_domestic_capacity_score",
                "strategic_importance_score": "b_strategic_importance_score",
                "notes": "b_notes",
                "sector": "b_sector",
            }
        )

        keep_a = [
            col
            for col in [
                "hs_code",
                "product_description",
                "a_sector",
                "a_tariff_rate",
                "a_domestic_capacity_score",
                "a_strategic_importance_score",
                "a_notes",
            ]
            if col in a.columns
        ]

        keep_b = [
            col
            for col in [
                "hs_code",
                "product_description",
                "b_sector",
                "b_tariff_rate",
                "b_domestic_capacity_score",
                "b_strategic_importance_score",
                "b_notes",
            ]
            if col in b.columns
        ]

        merged = a[keep_a].merge(
            b[keep_b],
            on="hs_code",
            how="inner",
            suffixes=("_a", "_b"),
        )

        if "product_description_a" in merged.columns:
            merged["product_description"] = merged["product_description_a"].fillna(
                merged.get("product_description_b")
            )
            merged = merged.drop(
                columns=[
                    col
                    for col in ["product_description_a", "product_description_b"]
                    if col in merged.columns
                ]
            )

        merged = merged.merge(trade_flows, on="hs_code", how="left")
        merged[["exports_a_to_b", "exports_b_to_a"]] = merged[
            ["exports_a_to_b", "exports_b_to_a"]
        ].fillna(0)

        optional_trade_cols = ["world_imports_a", "world_imports_b"]
        for col in optional_trade_cols:
            if col in merged.columns:
                merged[col] = merged[col].fillna(0)

        if merged.empty:
            raise ValueError(
                "No matching HS codes were found across tariff schedules and trade-flow data."
            )

        return merged

    def score(
        self,
        country_a_tariffs: pd.DataFrame,
        country_b_tariffs: pd.DataFrame,
        trade_flows: pd.DataFrame,
    ) -> pd.DataFrame:
        """Return product-level scores and strategy recommendations."""
        model_data = self.prepare_model_data(country_a_tariffs, country_b_tariffs, trade_flows)
        scores = score_product_lines(model_data, self.weights)

        preferred_columns = [
            "hs_code",
            "product_description",
            "a_sector",
            "a_tariff_rate",
            "b_tariff_rate",
            "a_domestic_capacity_score",
            "b_domestic_capacity_score",
            "a_strategic_importance_score",
            "b_strategic_importance_score",
            "exports_a_to_b",
            "exports_b_to_a",
            "a_offensive_priority",
            "a_defensive_sensitivity",
            "b_offensive_priority",
            "a_concession_value",
            "a_net_negotiating_value",
            "recommended_a_strategy",
            "analyst_rationale",
        ]

        existing = [col for col in preferred_columns if col in scores.columns]
        remaining = [col for col in scores.columns if col not in existing]
        return scores[existing + remaining].sort_values(
            by=["a_offensive_priority", "a_net_negotiating_value"], ascending=[False, False]
        )

    def recommend_packages(
        self,
        scores: pd.DataFrame,
        max_packages: int = 10,
    ) -> pd.DataFrame:
        """Create simple ask-for-concession package pairings.

        The package logic pairs Country A's highest-priority asks with products that
        Country A could potentially concede. It is intentionally transparent so that
        analysts can revise the pairings based on politics, legal constraints, sector
        strategy, and negotiating context.
        """
        asks = scores[
            scores["recommended_a_strategy"].isin(
                ["Priority ask from Country B", "High-value reciprocal tradeoff"]
            )
        ].copy()
        if asks.empty:
            asks = scores.nlargest(5, "a_offensive_priority").copy()

        concessions = scores[
            scores["recommended_a_strategy"].isin(
                ["Possible concession / bargaining chip", "Balanced negotiation item"]
            )
        ].copy()
        if concessions.empty:
            concessions = scores.nsmallest(5, "a_defensive_sensitivity").copy()

        asks = asks.sort_values("a_offensive_priority", ascending=False).head(max_packages)
        concessions = concessions.sort_values("a_concession_value", ascending=False).head(
            max_packages
        )

        records: list[dict[str, object]] = []
        for ask_row, concession_row in zip(asks.to_dict("records"), concessions.to_dict("records")):
            package_balance = round(
                float(ask_row["a_offensive_priority"])
                - float(concession_row["a_defensive_sensitivity"]),
                2,
            )
            records.append(
                {
                    "package_type": "Ask-for-concession package",
                    "a_ask_hs_code": ask_row["hs_code"],
                    "a_ask_product": ask_row["product_description"],
                    "a_ask_score": ask_row["a_offensive_priority"],
                    "a_possible_concession_hs_code": concession_row["hs_code"],
                    "a_possible_concession_product": concession_row[
                        "product_description"
                    ],
                    "concession_value": concession_row["a_concession_value"],
                    "concession_sensitivity": concession_row[
                        "a_defensive_sensitivity"
                    ],
                    "package_balance_score": package_balance,
                    "package_note": (
                        "Positive balance means the ask score exceeds the domestic "
                        "sensitivity of the possible concession."
                    ),
                }
            )

        return pd.DataFrame(records)

    def run_from_files(
        self,
        country_a_tariffs_path: str | Path,
        country_b_tariffs_path: str | Path,
        trade_flows_path: str | Path,
        out_dir: str | Path = "output",
    ) -> tuple[pd.DataFrame, pd.DataFrame, str]:
        """Load data, calculate scores, produce packages, and write output files."""
        country_a_tariffs, country_b_tariffs, trade_flows = load_inputs(
            country_a_tariffs_path,
            country_b_tariffs_path,
            trade_flows_path,
        )
        scores = self.score(country_a_tariffs, country_b_tariffs, trade_flows)
        packages = self.recommend_packages(scores)
        report = build_markdown_report(
            scores=scores,
            packages=packages,
            country_a_name=self.country_a_name,
            country_b_name=self.country_b_name,
        )
        write_outputs(scores, packages, report, out_dir)
        return scores, packages, report
