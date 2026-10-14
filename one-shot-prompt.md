# RI Commitment Explorer - One-Shot Build Prompt

Build a small Streamlit decision-support tool called **RI Commitment Explorer**. The user is a FinOps manager at Riot Games deciding which public AWS price option is worth investigating for a stable baseline of Linux C6i compute capacity in `us-east-1`. This is a transparent public-list-price scenario, not a purchase recommendation and not a replacement for Riot's billing data or AWS Cost Explorer.

## User decision and expected interaction

The manager chooses one non-bare-metal Linux C6i instance type and an assumed utilization from 0% to 100%. The tool shows the matching public On-Demand price beside every available one-year and three-year **Standard** Reserved Instance payment option. For each option, show the upfront payment, recurring RI hourly price, effective RI hourly price, annualized RI cost, the On-Demand annual cost at the stated utilization, annual savings versus On-Demand, and break-even utilization. The manager then decides whether an option is worth checking against Riot's internal usage, billing, discounts, existing commitments, and workload plans.

On first load, state the scope and show the two inputs. Do not show a recommendation until both are valid. On every input change, recompute the scenario immediately from a small processed table; do not reopen the raw AWS CSV.

## Scope and non-goals

The first release includes only rows where `Product Family = Compute Instance`, `Region Code = us-east-1`, `Operating System = Linux`, `Tenancy = Shared`, `CapacityStatus = Used`, `Pre Installed S/W = NA`, and `Instance Type` starts with `c6i.`. This deliberately excludes `c6i.metal`, convertible RIs, other regions, other operating systems, Savings Plans, Spot, and fleet-size estimates. Every displayed result is per C6i instance-equivalent and in USD.

The UI must visibly say that AWS public list prices do not contain Riot's private discounts, credits, actual usage, existing commitments, performance requirements, or demand forecast. Its next action is “investigate with internal data,” never “buy this RI.” Keep the AWS publication date and version visible with the result.

## Architecture and team boundaries

The app has two layers:

```text
Prepare once: full AWS EC2 regional CSV
  -> filter and normalize C6i rate components
  -> pair RI components and calculate price-option table

Run interactively: processed price-option table
  -> selected instance type + utilization
  -> cost comparison table and concise decision view
```

The data-and-formula group of three owns `01-data-filtering.md` and `02-cost-formulas.md`. Their final handoff is `data/processed/c6i_price_options.parquet` plus a validation report. The UI group of three owns loading that table, the comparison table, and the page layout. UI code may not duplicate parsing, filtering, RI pairing, or cost formulas.

## Data preparation requirements

Use the full regional price list at `data/ec2_us-east-1.csv`, not `sample/ec2_us-east-1_sample.csv`. If it is absent, download only the regional file from `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.csv`; never use the all-region EC2 URL. The sample is a random subset and breaks the two-row Reserved Instance relationship. Read the first five rows as metadata, then read the CSV with `skiprows=5`, `dtype=str`, `keep_default_na=False`, and `low_memory=False`.

Filter to the scope above. Keep On-Demand rows only when `TermType = OnDemand` and `Unit = Hrs`. Keep Reserved rows only when `TermType = Reserved`, normalized `OfferingClass = standard`, normalized lease length is `1yr` or `3yr`, and `Unit` is `Hrs` or `Quantity`. Normalize spaced and unspaced term and payment labels before grouping.

For each RI group identified by `SKU + OfferTermCode`, use its one `Hrs` component as recurring price and its `Quantity` component as upfront price. A No Upfront option without a `Quantity` component has upfront price zero. Do not guess when a group is malformed: report missing or duplicate components and exclude that option. Each valid option must have exactly one comparable On-Demand hourly price for the same instance type.

## Shared data contract and formulas

The processed table must contain `price_list_version`, `publication_date`, `instance_type`, `term_years`, `purchase_option`, `offering_class`, `on_demand_hourly_usd`, `ri_upfront_usd`, `ri_hourly_usd`, and `effective_ri_hourly_usd`. Store monetary values as decimals or decimal strings; do not perform financial comparisons with binary floats.

For a term of `term_years`:

```text
term_hours               = 8,760 × term_years
effective_ri_hourly      = ri_hourly + ri_upfront / term_hours
ri_annualized_cost       = effective_ri_hourly × 8,760
on_demand_annual_cost    = on_demand_hourly × 8,760 × utilization
annual_savings_vs_od     = on_demand_annual_cost - ri_annualized_cost
break_even_utilization   = effective_ri_hourly / on_demand_hourly
```

An option is economical under the entered assumption only if utilization is at least break-even and annual savings are positive. Negative savings remain visible as a cost increase. All Upfront may legitimately have a zero recurring hourly charge. Reject utilization outside 0 to 1 and reject zero or negative On-Demand price before computing break-even.

## UI requirements

Load and cache only `c6i_price_options.parquet`. Provide an instance-type selector and a percent-formatted utilization input. Render a comparison table with one row per RI option, ordered by term then payment option, and make clear that a three-year figure is annualized for comparison. Show the current source version, scope boundary, and a readable empty state when no option is available. A compact chart is optional; the comparison table and clear calculation labels are required.

## Build order and done checks

1. Build and test the raw-data parser and metadata reader against the full regional file.
2. Filter and normalize rate components; write a validation report with retained counts and invalid keys.
3. Pair RI components, create the processed price-option table, and test the formulas with invented data.
4. Build the loader and UI against only the processed table.
5. Confirm that changing utilization does not read raw data, the displayed figures agree with the pure functions, invalid inputs are rejected, and every result has a version and limitation notice.

The work is done when a fresh clone can build the processed table from the full regional file, run the app, choose a C6i instance type and utilization, and see internally consistent public-price comparisons without any claim about Riot's actual bill or purchase decision.
