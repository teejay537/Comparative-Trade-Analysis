from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from trade_strategy_model import TradeStrategyModel  # noqa: E402


def test_model_scores_sample_data():
    model = TradeStrategyModel()
    scores, packages, report = model.run_from_files(
        country_a_tariffs_path=PROJECT_ROOT / "data" / "country_a_tariffs.csv",
        country_b_tariffs_path=PROJECT_ROOT / "data" / "country_b_tariffs.csv",
        trade_flows_path=PROJECT_ROOT / "data" / "bilateral_trade_flows.csv",
        out_dir=PROJECT_ROOT / "output" / "test_run",
    )

    assert isinstance(scores, pd.DataFrame)
    assert not scores.empty
    assert "a_offensive_priority" in scores.columns
    assert scores["a_offensive_priority"].between(0, 100).all()
    assert "recommended_a_strategy" in scores.columns
    assert isinstance(packages, pd.DataFrame)
    assert "Bilateral Goods Trade Negotiation Report" in report


def test_prepare_model_data_requires_matching_hs_codes():
    model = TradeStrategyModel()
    a = pd.DataFrame(
        {
            "hs_code": ["111111"],
            "product_description": ["A product"],
            "tariff_rate": [5],
            "domestic_capacity_score": [50],
            "strategic_importance_score": [50],
        }
    )
    b = pd.DataFrame(
        {
            "hs_code": ["222222"],
            "product_description": ["B product"],
            "tariff_rate": [5],
            "domestic_capacity_score": [50],
            "strategic_importance_score": [50],
        }
    )
    flows = pd.DataFrame(
        {
            "hs_code": ["111111"],
            "exports_a_to_b": [1000],
            "exports_b_to_a": [2000],
        }
    )

    try:
        model.prepare_model_data(a, b, flows)
    except ValueError as exc:
        assert "No matching HS codes" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-matching HS codes")
