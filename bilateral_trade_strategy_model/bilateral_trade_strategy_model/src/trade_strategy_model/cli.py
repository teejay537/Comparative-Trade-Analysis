"""Command-line interface for the bilateral trade strategy model."""

from __future__ import annotations

import argparse
from pathlib import Path

from .model import TradeStrategyModel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate bilateral goods tariff-negotiation priorities."
    )
    parser.add_argument(
        "--country-a-tariffs",
        required=True,
        help="Path to Country A tariff schedule CSV.",
    )
    parser.add_argument(
        "--country-b-tariffs",
        required=True,
        help="Path to Country B tariff schedule CSV.",
    )
    parser.add_argument(
        "--trade-flows",
        required=True,
        help="Path to bilateral trade-flow CSV.",
    )
    parser.add_argument(
        "--country-a-name",
        default="Country A",
        help="Display name for Country A.",
    )
    parser.add_argument(
        "--country-b-name",
        default="Country B",
        help="Display name for Country B.",
    )
    parser.add_argument(
        "--out-dir",
        default="output",
        help="Folder for model outputs.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    model = TradeStrategyModel(
        country_a_name=args.country_a_name,
        country_b_name=args.country_b_name,
    )
    scores, packages, _ = model.run_from_files(
        country_a_tariffs_path=args.country_a_tariffs,
        country_b_tariffs_path=args.country_b_tariffs,
        trade_flows_path=args.trade_flows,
        out_dir=args.out_dir,
    )

    output_path = Path(args.out_dir).resolve()
    print("Model run complete.")
    print(f"Product lines scored: {len(scores)}")
    print(f"Packages suggested: {len(packages)}")
    print(f"Outputs written to: {output_path}")
    print("\nTop 5 Country A asks:")
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
        .head(5)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
