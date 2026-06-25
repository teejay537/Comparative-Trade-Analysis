"""Input/output and validation helpers for the trade strategy model."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

REQUIRED_TARIFF_COLUMNS = {
    "hs_code",
    "product_description",
    "tariff_rate",
    "domestic_capacity_score",
    "strategic_importance_score",
}

REQUIRED_TRADE_FLOW_COLUMNS = {
    "hs_code",
    "exports_a_to_b",
    "exports_b_to_a",
}


def read_csv(path: str | Path) -> pd.DataFrame:
    """Read a CSV file and keep HS codes as text so leading zeros are preserved."""
    return pd.read_csv(path, dtype={"hs_code": "string"})


def require_columns(df: pd.DataFrame, required_columns: Iterable[str], dataset_name: str) -> None:
    """Raise a helpful error when an input file is missing required columns."""
    missing = sorted(set(required_columns) - set(df.columns))
    if missing:
        raise ValueError(
            f"{dataset_name} is missing required column(s): {', '.join(missing)}"
        )


def clean_tariff_schedule(df: pd.DataFrame, country_label: str) -> pd.DataFrame:
    """Validate and clean one country's tariff schedule."""
    require_columns(df, REQUIRED_TARIFF_COLUMNS, f"{country_label} tariff schedule")

    cleaned = df.copy()
    cleaned["hs_code"] = cleaned["hs_code"].astype("string").str.strip()
    cleaned["product_description"] = cleaned["product_description"].astype("string").str.strip()

    numeric_cols = [
        "tariff_rate",
        "domestic_capacity_score",
        "strategic_importance_score",
    ]
    for col in numeric_cols:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    if cleaned[numeric_cols].isna().any().any():
        bad_cols = cleaned[numeric_cols].columns[cleaned[numeric_cols].isna().any()].tolist()
        raise ValueError(
            f"{country_label} tariff schedule contains non-numeric or blank values in: "
            f"{', '.join(bad_cols)}"
        )

    if not cleaned["tariff_rate"].between(0, 100).all():
        raise ValueError(f"{country_label} tariff_rate must be between 0 and 100.")

    for col in ["domestic_capacity_score", "strategic_importance_score"]:
        if not cleaned[col].between(0, 100).all():
            raise ValueError(f"{country_label} {col} must be between 0 and 100.")

    return cleaned


def clean_trade_flows(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and clean bilateral trade-flow data."""
    require_columns(df, REQUIRED_TRADE_FLOW_COLUMNS, "bilateral trade-flow data")

    cleaned = df.copy()
    cleaned["hs_code"] = cleaned["hs_code"].astype("string").str.strip()

    numeric_cols = ["exports_a_to_b", "exports_b_to_a"]
    optional_numeric = ["world_imports_a", "world_imports_b"]
    numeric_cols.extend([col for col in optional_numeric if col in cleaned.columns])

    for col in numeric_cols:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce").fillna(0)
        if (cleaned[col] < 0).any():
            raise ValueError(f"{col} cannot contain negative values.")

    return cleaned


def load_inputs(
    country_a_tariffs_path: str | Path,
    country_b_tariffs_path: str | Path,
    trade_flows_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and validate all model input files."""
    country_a_tariffs = clean_tariff_schedule(
        read_csv(country_a_tariffs_path), country_label="Country A"
    )
    country_b_tariffs = clean_tariff_schedule(
        read_csv(country_b_tariffs_path), country_label="Country B"
    )
    trade_flows = clean_trade_flows(read_csv(trade_flows_path))
    return country_a_tariffs, country_b_tariffs, trade_flows


def write_outputs(
    scores: pd.DataFrame,
    packages: pd.DataFrame,
    report_markdown: str,
    out_dir: str | Path,
) -> None:
    """Write model outputs to a folder."""
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    scores.to_csv(output_path / "negotiation_scores.csv", index=False)
    packages.to_csv(output_path / "recommended_packages.csv", index=False)
    (output_path / "negotiation_report.md").write_text(report_markdown, encoding="utf-8")
