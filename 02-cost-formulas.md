# 02 - Cost formulas contract

## Purpose

This file turns the normalized components from `01-data-filtering.md` into one comparable public-price option per C6i instance type, RI term, and payment option. All arithmetic uses decimal currency values. The formulas are pure: they receive data and an assumption, return data, and never read files, widgets, or session state.

## Input and price-option output

Read `data/processed/c6i_filtered_rate_components.parquet`. For each `instance_type`, find exactly one On-Demand `Hrs` component. For each Standard RI group identified by `sku + offer_term_code`:

- `Hrs` is the recurring RI hourly charge and must occur exactly once.
- `Quantity` is the upfront RI charge and must occur at most once.
- A No Upfront option with no `Quantity` component has `ri_upfront_usd = 0`.
- Missing, duplicate, or conflicting required components make the option invalid. Report it; do not guess or average.

Join each valid RI group to the unique On-Demand rate for its `instance_type`. Write the resulting table to `data/processed/c6i_price_options.parquet` with one row per valid RI option:

| Column | Meaning |
| --- | --- |
| `price_list_version`, `publication_date`, `instance_type` | Source identity and selected product |
| `term_years`, `purchase_option`, `offering_class` | RI contract attributes |
| `on_demand_hourly_usd` | Comparable On-Demand hourly list price |
| `ri_upfront_usd`, `ri_hourly_usd` | RI payment components |
| `effective_ri_hourly_usd` | RI price normalized across its full term |

The table is the only pricing data the UI may load. It contains public list prices, not Riot billing data.

## Formulas

For an RI option with a one- or three-year term:

```text
term_hours               = 8,760 × term_years
effective_ri_hourly      = ri_hourly + ri_upfront / term_hours
ri_annualized_cost       = effective_ri_hourly × 8,760
```

The front end supplies one scenario input, `utilization`, as a decimal from 0 to 1. The scenario comparison is:

```text
on_demand_annual_cost    = on_demand_hourly × 8,760 × utilization
annual_savings_vs_od     = on_demand_annual_cost - ri_annualized_cost
break_even_utilization   = effective_ri_hourly / on_demand_hourly
```

Display an option as economical under the stated assumption only when `utilization >= break_even_utilization` and `annual_savings_vs_od > 0`. A three-year option is annualized only to make it comparable; its full term and upfront amount must remain visible.

## Edge cases and tests

- Reject utilization below 0 or above 1.
- Reject a zero or negative On-Demand hourly rate before calculating break-even utilization.
- Allow a zero RI hourly rate for All Upfront; its upfront component is still required.
- Keep negative savings visible as a cost increase; never relabel it as savings.
- Round only for display. Store and compare decimal values without float rounding.
- Test one invented No Upfront, Partial Upfront, and All Upfront option for both one and three years. Verify the effective rate, annualized RI cost, break-even point, and sign of savings.
- Test malformed component groups separately: missing `Hrs`, duplicate `Hrs`, duplicate `Quantity`, and no matching On-Demand baseline must all be reported rather than silently removed.

## Three-person formula-work split

1. **Pairing owner:** implements RI grouping, upfront/hourly extraction, and the price-option table.
2. **Calculation owner:** implements decimal cost and break-even functions with invented-data tests.
3. **Quality owner:** checks source-version propagation, invalid-group reporting, and the output schema consumed by the UI team.
