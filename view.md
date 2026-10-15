# View contract — RI Commitment Explorer

## Purpose

Build the result presentation in `src/views.py` for the single-page
Streamlit application. Help the FinOps manager compare available Standard
RI options for one C6i configuration and understand how the stated runtime
assumption affects the comparison.

View receives calculated data. It does not read the raw CSV or Parquet,
filter raw prices, pair RI components, or redefine financial formulas.

## Upstream handoff

The existing contracts remain the source for data and calculations:

```text
01-data-filtering.md
  -> c6i_filtered_rate_components.parquet
02-cost-formulas.md: pairing and price normalization
  -> c6i_price_options.parquet
Loader + scenario calculation
  -> result DataFrame
View
  -> displayed comparison
```

`02` defines the prepared price fields. The integrated one-shot prompt's
Scenario calculation contract adds the runtime-dependent result fields.
Dashboard calls that calculator and passes the result to View; View never
loads either intermediate file itself.

## Interface

```python
from decimal import Decimal
import pandas as pd

def render_comparison(
    results: pd.DataFrame,
    instance_type: str,
    utilization: Decimal,
) -> None:
    ...
```

Dashboard passes valid inputs: one selected instance and runtime as a
fraction from 0 to 1. View displays that fraction as a percentage. View
does not create input controls or convert user input for the calculator.

Required result columns:

| Field | Display or use |
|---|---|
| price_list_version, publication_date | Source identity |
| instance_type | Selected configuration |
| term_years | Separate one-year and three-year sections |
| purchase_option | Purchase option |
| offering_class | Standard RI scope |
| on_demand_hourly_usd | Comparable On-Demand rate |
| ri_upfront_usd | Upfront payment |
| ri_hourly_usd | Recurring RI hourly rate |
| effective_ri_hourly_usd | Effective RI hourly cost |
| ri_annualized_cost_usd | Annualized RI cost |
| on_demand_annual_cost_usd | On-Demand annual cost at assumed runtime |
| annual_savings_vs_od_usd | Annual savings versus On-Demand |
| break_even_utilization | Break-even runtime percentage |
| comparison_status | Calculator's cost comparison classification |

Monetary fields and break-even values arrive as Decimal values. Preserve
the input DataFrame; use a separate display table for formatted values.
Do not recompute comparison_status from rounded display values.

## Screen content

Show the selected instance, expected runtime, matching On-Demand hourly
rate, source version, and publication date. State the fixed scope:
us-east-1, Linux, Shared tenancy, Used capacity, no pre-installed software,
and non-bare-metal C6i. Region is information, not a selector.

Render one-year and three-year sections. Each row is one available RI
option. Order payment options as No Upfront, Partial Upfront, All Upfront.
Include all cost, savings, break-even, and status fields listed above.
Allow horizontal scrolling for the result table on narrow screens.

Unavailable payment options are not zero-price rows. If a term has no
options, state that no valid options are available for that term.

Keep annualized cost and upfront payment separate. Explain that annualized
cost spreads commitment charges across the term and is not an annual
payment schedule. Different commitment lengths carry different risks;
do not present an unconditional best plan.

A chart is optional. The comparison table is required. Leave decorative
styling to the builder.

## Formatting and interpretation

- Display money in USD. Show upfront and annual amounts to two decimals.
- Show hourly values with enough precision to avoid displaying a nonzero
  rate as zero; a legitimate zero recurring rate remains visible.
- Display runtime and break-even fractions as percentages. Add precision
  when needed to explain a near-threshold result; preserve calculator status.
- Keep negative savings signed and explain them as a modeled cost increase.
- For break-even above 100%, state that it is unattainable in the modeled
  runtime range. Do not clamp the value to 100%.
- Expected runtime is the share of term hours capacity is needed, not CPU
  utilization. RI costs remain payable when the capacity is unused.
- Label the data as an AWS published price snapshot, not live prices.

Include a concise notice that results are public-price scenarios, excluding
Riot's private discounts, credits, actual usage, existing commitments,
capital costs, and future workload changes. The next action is to investigate
with internal usage and billing data, not to purchase automatically.

## Empty states and responsibilities

Dashboard handles the initial unselected state and invalid user input.
Loader/Dashboard handles missing or invalid processed-file errors.

When View receives an empty result table with the expected schema, show
“No valid Reserved Instance options are available for this selection.”

Missing required fields, mismatched instance rows, or inconsistent source
metadata indicate a handoff error. Show an explanatory error rather than
a partial comparison. Never substitute zero for missing prices.

## Acceptance checks

Use calculator result fixtures, not the random AWS sample, to check display.

| Fixture | Required display |
|---|---|
| One-year No Upfront; OD $0.20/h, RI $0.12/h, upfront $0, runtime 80% | RI annualized $1,051.20; OD annual $1,401.60; savings $350.40; break-even 60% |
| Same option, runtime 60% | Savings $0.00; Break-even status |
| Same option, runtime 50% | Savings -$175.20; On-Demand lower modeled cost |
| Three-year All Upfront; OD $0.20/h, upfront $1,576.80, recurring $0/h, runtime 80% | Full upfront $1,576.80; effective $0.06/h; annualized $525.60; savings $876.00; break-even 30% |

Also check separate term sections, canonical payment ordering, source
metadata, empty results, break-even above 100%, missing-field errors,
and preservation of the original input table.

Changing runtime must update displayed results through Dashboard and the
calculator without View opening files or modifying prices. These are
required checks for the later implementation, not completed test results.
