# Bilateral Goods Trade-Agreement Strategy Model

A small Python project for evaluating tariff-negotiation priorities and tradeoffs in a bilateral goods trade agreement.

The model compares each country's tariff schedule, domestic productive capacity, strategic importance scores, and bilateral trade-flow data. It produces product-level negotiating scores and suggested tradeoff packages for a tariff negotiation.

## What the model does

For each HS/product line, the model calculates from the perspective of Country A:

1. **A offensive priority**: how strongly Country A should ask Country B to reduce tariffs on that product.
2. **A defensive sensitivity**: how costly or politically sensitive it may be for Country A to reduce its own tariff on that product.
3. **B offensive priority**: how strongly Country B is likely to ask Country A to reduce tariffs.
4. **A concession value**: whether Country A can offer tariff reductions on a product with relatively low domestic sensitivity.
5. **Recommended A strategy**: priority ask, protect/red-line, bargaining chip, reciprocal tradeoff, or low-priority item.

The output is intended to help analysts build a negotiating position, not to replace expert judgment.

## Project structure

```text
bilateral_trade_strategy_model/
├── data/
│   ├── country_a_tariffs.csv
│   ├── country_b_tariffs.csv
│   └── bilateral_trade_flows.csv
├── examples/
│   └── run_sample.py
├── output/
│   ├── negotiation_scores.csv
│   ├── recommended_packages.csv
│   └── negotiation_report.md
├── src/
│   └── trade_strategy_model/
│       ├── __init__.py
│       ├── cli.py
│       ├── io.py
│       ├── model.py
│       ├── reporting.py
│       └── scoring.py
├── tests/
│   └── test_model.py
├── requirements.txt
└── pyproject.toml
```

## Input files

### Tariff schedule files

Country tariff files must contain these columns:

| Column | Meaning |
|---|---|
| `hs_code` | Product code, such as HS 6-digit code |
| `product_description` | Product description |
| `tariff_rate` | Applied tariff rate as a percentage, for example `12.5` |
| `domestic_capacity_score` | 0-100 score for domestic ability to produce the product |
| `strategic_importance_score` | 0-100 score for strategic/economic/political importance |

Optional tariff file columns:

| Column | Meaning |
|---|---|
| `notes` | Analyst comments |
| `sector` | Sector/category used for reporting |

### Bilateral trade-flow file

The trade-flow file must contain these columns:

| Column | Meaning |
|---|---|
| `hs_code` | Product code matching the tariff files |
| `exports_a_to_b` | Country A exports to Country B, in any consistent currency/unit |
| `exports_b_to_a` | Country B exports to Country A, in the same currency/unit |

Optional trade-flow columns:

| Column | Meaning |
|---|---|
| `world_imports_a` | Country A imports of the product from the world |
| `world_imports_b` | Country B imports of the product from the world |

## Installation

From the project folder:

```bash
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate # macOS/Linux

python -m pip install -r requirements.txt
python -m pip install -e .
```

## Run the sample model

```bash
python examples/run_sample.py
```

Or run through the command line interface:

```bash
python -m trade_strategy_model.cli \
  --country-a-tariffs data/country_a_tariffs.csv \
  --country-b-tariffs data/country_b_tariffs.csv \
  --trade-flows data/bilateral_trade_flows.csv \
  --country-a-name CountryA \
  --country-b-name CountryB \
  --out-dir output
```

## Outputs

The model writes three files to the output folder:

1. `negotiation_scores.csv` - product-level scores and recommendations.
2. `recommended_packages.csv` - possible ask/concession package pairings.
3. `negotiation_report.md` - plain-English markdown report.

## Interpreting the main output fields

| Field | Meaning |
|---|---|
| `a_offensive_priority` | Country A's interest in obtaining tariff cuts from Country B |
| `a_defensive_sensitivity` | Country A's sensitivity to cutting its own tariff |
| `b_offensive_priority` | Country B's likely interest in asking Country A for tariff cuts |
| `a_concession_value` | Products Country A may concede with relatively low domestic cost |
| `a_net_negotiating_value` | A offensive priority minus A defensive sensitivity |
| `recommended_a_strategy` | Suggested treatment in negotiations |

## Method summary

The model normalizes tariffs, capacity scores, strategic scores, and trade flows to a 0-1 scale. It then calculates weighted composite scores:

- Offensive interest rises when the partner tariff is high, domestic capacity is strong, strategic importance is high, and current exports already exist.
- Defensive sensitivity rises when the home tariff is high, domestic capacity is strong, strategic importance is high, and partner exports into the home market are material.
- Concession value rises when the partner wants market access but the home country's defensive sensitivity is relatively low.

The default weights are defined in `src/trade_strategy_model/scoring.py` and can be edited.

## Customizing the model

You can adjust the weights in `ScoreWeights` in `scoring.py`, or pass a custom `ScoreWeights` object from your own script. For example, increase `strategic_importance_weight` if strategic products should dominate the negotiating strategy.

