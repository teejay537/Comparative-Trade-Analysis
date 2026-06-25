"""Run the sample bilateral trade strategy model."""

from pathlib import Path
import sys

# Allow this example to run directly before package installation.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from trade_strategy_model import TradeStrategyModel  # noqa: E402


def main() -> None:
    model = TradeStrategyModel(
        country_a_name="Country A",
        country_b_name="Country B",
    )

    scores, packages, _ = model.run_from_files(
        country_a_tariffs_path=PROJECT_ROOT / "data" / "country_a_tariffs.csv",
        country_b_tariffs_path=PROJECT_ROOT / "data" / "country_b_tariffs.csv",
        trade_flows_path=PROJECT_ROOT / "data" / "bilateral_trade_flows.csv",
        out_dir=PROJECT_ROOT / "output",
    )

    print("Sample model run complete.")
    print("\nTop priority asks from Country A's perspective:")
    print(
        scores[
            [
                "hs_code",
                "product_description",
                "a_offensive_priority",
                "a_defensive_sensitivity",
                "recommended_a_strategy",
            ]
        ]
        .head(8)
        .to_string(index=False)
    )

    print("\nSuggested packages:")
    if packages.empty:
        print("No packages suggested.")
    else:
        print(
            packages[
                [
                    "a_ask_hs_code",
                    "a_ask_product",
                    "a_possible_concession_hs_code",
                    "a_possible_concession_product",
                    "package_balance_score",
                ]
            ]
            .head(5)
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
