# RI Commitment Explorer — One-Shot Build Prompt

How to read this prompt: Vision and Design explain the product and
its reasoning. Pieces defines module boundaries. Details specifies
data rules, calculations, and interactions. Build order and Done when
define implementation and verification.

## Vision

**Who uses it.**

A FinOps / Procurement Manager at Riot Games, in a hypothetical
planning scenario where engineering has identified a Linux C6i
configuration in us-east-1 for a baseline workload.

**Why.**

The manager must assess whether to keep paying On-Demand or
investigate a one-year or three-year Standard Reserved Instance
commitment. Today, that comparison requires looking up prices,
combining upfront and recurring charges, and recalculating costs
under different usage assumptions.

The tool brings those steps into one screen. It compares purchase
options for the same configuration and shows when their modeled
savings disappear.

**What they care about.**

- Upfront payment and continuing hourly charges.
- Annualized commitment cost and savings versus On-Demand.
- The expected runtime needed to break even.
- Exposure to paying for capacity that is not needed.
- Clear distinctions between published prices, assumptions,
  and actual company costs.

**Common scenarios.**

- Select an engineering-approved C6i instance type and inspect its
  available Standard RI purchase options beside On-Demand.
- Lower expected runtime and see which options lose their modeled
  savings.
- Review the break-even threshold and commitment duration before
  investigating an option with internal usage and billing data.

The next action is “investigate with internal data,” not “buy this RI.”
This tool does not establish Riot's actual demand or recommend which
instance type meets its performance requirements.

## Design

Build a single-page Streamlit application with two inputs:
instance type and expected billable runtime percentage.

Region and other comparison attributes are fixed scope information,
not user-selectable controls.

```text
Prepare once
AWS EC2 regional CSV
  -> Reader / filtering / normalization (01 contract)
  -> c6i_filtered_rate_components.parquet + filtering report
  -> Pairing / price normalization (02 contract)
  -> c6i_price_options.parquet + validation report

When the app starts
Processed table -> Loader -> cached prices

On each input change
Cached prices + selected instance + runtime assumption
  -> Scenario calculation
  -> comparison results
  -> View
```

**Design principles**

1. **Compare like with like.** Hold the product configuration constant
   so hardware, software, and tenancy differences are not mistaken
   for purchase-plan savings.

2. **Prepare once; calculate on interaction.** Parsing and pairing
   happen before the app runs. Changing runtime must not scan the
   raw CSV or rebuild the processed table.

3. **Explicit contracts between pieces.** Calculations receive data
   and values; views receive calculated results. No piece depends
   on another piece's private implementation.

4. **One definition per measure.** Financial formulas belong in the
   calculation module. Views only format and display their results.

5. **Keep assumptions visible.** Runtime is entered by the user;
   it is not measured from Riot's systems.

6. **Prefer the smallest workable structure.** Use ordinary functions
   unless a class provides a clear benefit. This version does not
   need a generic filter framework, plug-in registry, setup page,
   saved presets, or multiple dashboards.

**Model assumptions**

- One selected instance-equivalent, not a fleet.
- Constant published rates throughout each modeled term.
- Constant expected runtime fraction throughout each term.
- 8,760 hours per modeled year; no leap-year adjustment.
- RI commitment charges remain payable regardless of runtime.
- No time-value-of-money adjustment.
- No private discounts, credits, existing commitment allocation,
  or modeled resale or exchange proceeds.
- No storage, network, tax, or other service charges.
- One-year and three-year plans cover different commitment periods;
  annualization does not make their risks equivalent.

## Pieces

### Preparation orchestration — src/prepare_data.py

Runs the two preparation stages below in order. It owns raw-file and
intermediate-file I/O, source metadata, and atomic output writes.
The stage functions receive DataFrames and return DataFrames and
validation findings; they do not perform file I/O.

### Reader, filtering, and normalization — src/filter_rates.py

Implements the existing 01-data-filtering.md contract.

Receives raw rate rows and source metadata. Returns comparable C6i
rate components without pairing charges or calculating costs.

The preparation command writes:

- data/processed/c6i_filtered_rate_components.parquet
- data/processed/filtering_report.json

### Pairing and price normalization — src/pair_rates.py

Implements the preparation portion of 02-cost-formulas.md.

Receives filtered components. Returns one valid price option per
instance type, RI term, and payment option, with its matching
On-Demand rate and effective RI hourly cost.

The preparation command writes:

- data/processed/c6i_price_options.parquet
- data/processed/validation_report.json

Filtering must not perform pairing. View must not duplicate either
stage. The financial definitions in Section E are shared by pairing
and interactive scenario calculation; do not implement competing
versions of the same formula.

### Loader — src/load_data.py

Receives the processed-table path.

Returns a validated price DataFrame.

It is the only application-runtime piece that opens the processed
data file. It does not download raw data, rebuild prices, or compute
usage scenarios.

### Scenario calculation — src/scenario.py

Receives prepared prices, one instance type, and runtime as a
fraction from 0 to 1.

Returns the scenario result table defined below.

It selects the requested instance from the prepared table and
performs runtime-dependent financial calculations using the prepared
price fields and the shared financial definitions. It does not read files,
access Streamlit, or mutate its input.

### View — src/views.py

Receives the result table and scenario context.

Displays costs, savings, break-even thresholds, source information,
and limitations.

It does not read data files or reimplement financial formulas.

### Dashboard — dashboard.py

Loads cached prices, draws the two controls, validates inputs,
calls the calculator, and passes results to View.

It owns orchestration and input conversion, not price parsing or
financial formulas.

## Details

### A. Data access and source metadata

Use the full regional file, not the random sample.

The default source path is:

../dataset_aws-price-list/data/ec2_us-east-1.csv

Resolve it relative to the team-project root. Accept --raw-path
to override it; never hard-code a teammate's home directory.

If the source is missing, the preparation command may download it
from:

https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.csv

Never use the all-region EC2 URL. Preserve an existing source file
unless an explicit refresh is requested.

Keep downloaded raw data out of Git.

Read the first five metadata lines and preserve the publication
date and version. Then read the CSV using:

```python
pd.read_csv(
    raw_path,
    skiprows=5,
    dtype=str,
    keep_default_na=False,
    low_memory=False,
)
```

Fail with an explanatory error if required metadata or columns
cannot be read.

The downloaded file is a price snapshot. Do not describe its prices
as live or imply that all rows have distinct price-change dates.

The local download inspected during planning contained 393,649 rows,
93 columns, and approximately 302.9 MB. These are planning observations,
not hard-coded acceptance criteria: record actual counts on each build.

### B. Fixed scope and normalization

Require:

```text
Product Family     = Compute Instance
Region Code        = us-east-1
Operating System   = Linux
Tenancy            = Shared
CapacityStatus     = Used
Pre Installed S/W  = NA
Instance Type      starts with c6i.
```

Explicitly exclude c6i.metal.

Keep On-Demand rows with TermType = OnDemand and Unit = Hrs.

Keep Reserved rows with:

- TermType = Reserved
- normalized OfferingClass = standard
- normalized lease length = 1yr or 3yr
- Unit = Hrs or Quantity

Normalize surrounding whitespace and the known spaced/unspaced
lease and payment labels.

Canonical payment labels are:

```text
No Upfront
Partial Upfront
All Upfront
```

Require USD prices. Validate numerical values as finite and
nonnegative. Reject unknown term or payment labels rather than
guessing their meaning.

Check rate-dimension applicability. Do not silently collapse multiple
tiers or distinct rates into one hourly price.

**Filtered-component handoff (01 contract)**

Write one row per retained AWS rate component to
data/processed/c6i_filtered_rate_components.parquet:

| Column | Type / meaning |
|---|---|
| price_list_version, publication_date | Source identity from metadata |
| sku, offer_term_code | String identifiers for later pairing |
| instance_type | C6i configuration identifier |
| term_type | OnDemand or Reserved |
| term_years | Null for On-Demand; integer 1 or 3 for RI |
| purchase_option | OnDemand, No Upfront, Partial Upfront, or All Upfront |
| offering_class | Null for On-Demand; standard for RI |
| unit | Hrs or Quantity |
| price_per_unit_usd | Exact source decimal string |

Filtering reports source identity, input and retained counts, retained
instance types, and excluded or ambiguous candidate rate keys with
reasons. Summarize ordinary out-of-scope exclusions by reason rather
than listing hundreds of thousands of unrelated rows.

Preserve rate identifiers in diagnostics so malformed source rows can
be traced. Stop with a clear availability error if the filtered output
has no comparable On-Demand row or no RI component.

### C. Pairing and validation

One raw row is a price component, not necessarily a complete
purchase option.

Group RI components by SKU and OfferTermCode within the source
snapshot.

For each group:

- Require exactly one Hrs component.
- Use its PricePerUnit as the recurring hourly rate.
- Require exactly one Quantity component for Partial Upfront and
  All Upfront.
- For No Upfront, an absent Quantity component means zero upfront
  payment; a present component must also be zero.
- Accept a zero recurring hourly rate, including valid All Upfront
  options.
- Require consistent configuration, term, and payment attributes
  within the group.

Match exactly one comparable On-Demand hourly price using the fixed
configuration and instance type. Do not resolve ambiguity by taking
the first, minimum, or average price.

Exclude invalid options and record their keys and reasons.
Do not silently fill missing prices with zero.

The validation report includes:

- Source file, publication date, and version.
- Raw row count and retained component counts.
- Valid option counts by instance, term, and payment option.
- Invalid or unmatched keys and exclusion reasons.
- Output row count and file size.

If no valid options remain, fail preparation with an explanatory
report rather than creating apparently usable empty data.

Write outputs atomically so a failed preparation does not replace
a valid processed file with a partial file.

### D. Processed price contract

Pairing consumes the filtered-component handoff, not the raw CSV.
The final processed table has one row per valid RI option for an
instance type, term, and payment option.

Required fields:

| Column | Meaning |
|---|---|
| price_list_version | Source version |
| publication_date | Source publication date |
| instance_type | Selected EC2 configuration identifier |
| term_years | Integer 1 or 3 |
| purchase_option | Canonical payment label |
| offering_class | standard |
| on_demand_hourly_usd | Comparable On-Demand runtime rate |
| ri_upfront_usd | Upfront payment |
| ri_hourly_usd | Recurring committed hourly rate |
| effective_ri_hourly_usd | Full-term normalized RI rate, calculated during preparation |

Preserve monetary fields as decimal strings in Parquet. Source
payment components retain their exact decimal values; the derived
effective rate uses the shared Decimal precision policy in Section E.
Convert directly to Decimal when calculating, never through a float.
Keep SKU and offer-term provenance in validation diagnostics; optional
extra provenance columns must not change the required UI contract.

If multiple otherwise valid offers share the same displayed
instance/term/payment combination, report the ambiguity and exclude
that combination from the MVP rather than silently merging it.

Loader validates the schema and source metadata. A missing or invalid
processed file produces instructions to run preparation; the app
must not silently fall back to sample or invented prices.

### E. Scenario calculation contract

```python
from decimal import Decimal
import pandas as pd

def calculate_scenario(
    price_options: pd.DataFrame,
    instance_type: str,
    utilization: Decimal,
) -> pd.DataFrame:
    ...
```

Utilization means expected billable runtime:

```text
0.80 = capacity is needed for 80% of modeled term hours
```

It is not CPU utilization. A machine running continuously with low
CPU usage does not receive a proportional On-Demand price reduction.

Reject non-finite inputs and values outside 0–1. Require a positive
On-Demand hourly price.

**Shared formulas (02 contract)**

Preparation computes effective_ri_hourly once using these definitions
and stores it as effective_ri_hourly_usd. Interactive calculation reads
that field; it must not redefine the normalization formula.

For each selected RI option, define:

```text
T = 8760 * term_years
p = on_demand_hourly_usd
h = ri_hourly_usd
F = ri_upfront_usd
u = utilization

ri_term_cost            = F + h * T
od_term_cost            = p * u * T
term_savings            = od_term_cost - ri_term_cost

effective_ri_hourly     = ri_term_cost / T
ri_annualized_cost      = ri_term_cost / term_years
on_demand_annual_cost   = od_term_cost / term_years
annual_savings_vs_od    = term_savings / term_years
break_even_utilization = ri_term_cost / (p * T)
```

Use Decimal arithmetic with explicit precision, at least 28 digits.
Do not round intermediate calculations for display.

Classify the comparison from unrounded term_savings, avoiding
classification based on a rounded effective hourly rate:

```text
positive -> RI lower modeled cost
zero     -> Break-even
negative -> On-Demand lower modeled cost
```

Preserve the prepared price fields, including effective_ri_hourly_usd,
and add these scenario fields:

```text
ri_annualized_cost_usd
on_demand_annual_cost_usd
annual_savings_vs_od_usd
break_even_utilization
comparison_status
```

Prepared monetary strings are converted to Decimal in the returned
result. Pass through the prepared effective_ri_hourly_usd field;
all computed numerical results remain Decimal values.

Return an empty table with the same schema when the selected
instance has no available valid RI options.

### F. View and interaction

On first load:

- Show the product title and fixed comparison scope.
- Leave instance selection unselected.
- Set expected runtime to 80%, labeled as an editable assumption.
- Show “Select an instance type to compare purchase options.”
- Do not calculate results until both inputs are valid.

Offer only instances present in the validated processed table.

The second input is labeled:

Expected billable runtime (%)

Its help text explains runtime versus CPU utilization.

Dashboard converts the input to a Decimal fraction, for example:

```python
utilization = Decimal(str(runtime_percent)) / Decimal("100")
```

On every valid input change, call the calculator using cached prices.

Show the selected instance and matching On-Demand hourly rate, then
separate one-year and three-year result sections.

Within each section, order rows:

```text
No Upfront
Partial Upfront
All Upfront
```

Display:

- Purchase option.
- Upfront payment.
- Recurring RI hourly rate.
- Effective RI hourly cost.
- Annualized RI cost.
- On-Demand annual cost at the entered runtime.
- Annual savings versus On-Demand.
- Break-even runtime.
- Comparison status.

Label annualized cost as an allocation across the commitment term,
not an annual payment schedule. Keep upfront payment separate.

Show annual amounts to two decimal places. Show hourly prices with
sufficient precision to avoid turning nonzero rates into apparent
zeros. Show runtime and break-even as percentages.

Formatting must not affect calculation or classification.

Keep negative savings visible. Explain break-even above 100% as
unattainable within the modeled runtime range.

Do not rank one-year and three-year plans by total dollars or name
an unconditional “best plan.” Present their costs and duration
together for further investigation.

Show the source publication date and version with the results.

Display a concise limitation notice and next action:
validate expected runtime, existing commitments, and negotiated
pricing with internal data before making a purchasing decision.

Distinguish:

- No instance selected.
- No valid option available.
- Missing or invalid processed file.

A chart is optional. The comparison table is required.
Styling and minor wording are left to the builder.

### G. Environment, caching, and deployment

Use:

- pandas for preparation and small-table selection.
- pyarrow for Parquet.
- Decimal for financial arithmetic.
- Streamlit for the interface.
- pytest for calculation and data-validation tests.

A SQL layer is unnecessary for the small prepared MVP table.
Do not retain the full raw CSV in application memory.

Create an independent uv project with dependency and lock files.
Support and document:

```bash
uv sync

uv run python -m src.prepare_data
uv run python -m src.prepare_data --raw-path /path/to/ec2_us-east-1.csv

uv run streamlit run dashboard.py
uv run pytest
```

Cache the processed table using its path and file identity, including
modification time and size, so replacing it invalidates the cache.
User interactions must not reopen raw data or write data files.

Current inputs live in session memory. Persistence between visits
is not required.

For later cloud deployment, prepare the table before deployment
and make its location configurable. The cloud app loads the small
processed table rather than downloading and parsing raw AWS data
during startup.

## Folder structure

```text
src/
    __init__.py
    prepare_data.py
    filter_rates.py
    pair_rates.py
    load_data.py
    scenario.py
    views.py
data/
    processed/
        c6i_filtered_rate_components.parquet
        filtering_report.json
        c6i_price_options.parquet
        validation_report.json
tests/
dashboard.py
README.md
one-shot-prompt.md
pyproject.toml
uv.lock
.gitignore
```

Raw downloads, local environments, and caches remain outside Git.

## Build order

1. Read the full regional file and validate metadata and schema.
2. Implement the 01 filtering contract and write the component table
   and filtering report.
3. Implement the 02 pairing contract and write the price-option table
   and validation report.
4. Implement the pure scenario calculator and check known fixtures.
5. Build Loader and View against their contracts.
6. Connect controls and verify complete user scenarios.
7. Write README instructions for preparation, startup, refresh,
   and the main files to read.

## Done when

A fresh clone can prepare data and run the app using only this prompt,
the dataset repository, and documented dependencies.

**Calculation fixture: one-year No Upfront**

```text
On-Demand hourly price = $0.20
RI hourly price        = $0.12
Upfront payment        = $0
Term                   = 1 year
Runtime                = 80%

Expected:
Effective RI hourly    = $0.12
Annualized RI cost     = $1,051.20
On-Demand annual cost  = $1,401.60
Annual savings         = $350.40
Break-even runtime     = 60%
Status                 = RI lower modeled cost
```

At 60%, savings must be zero and status must be Break-even.
At 50%, savings must be -$175.20 and On-Demand must be lower.

**Calculation fixture: three-year All Upfront**

```text
On-Demand hourly price = $0.20
RI hourly price        = $0
Upfront payment        = $1,576.80
Term                   = 3 years
Runtime                = 80%

Expected:
Effective RI hourly    = $0.06
Annualized RI cost     = $525.60
On-Demand annual cost  = $1,401.60
Annual savings         = $876.00
Break-even runtime     = 30%
```

The View must show the full $1,576.80 upfront payment separately
from the $525.60 annualized cost.

Also test invented No Upfront, Partial Upfront, and All Upfront
options for both one-year and three-year terms. Independently verify
effective rates, annualized costs, break-even, and savings signs.
Include missing Hrs, duplicate Hrs, duplicate Quantity, missing
required upfront charges, and absent or ambiguous On-Demand matches.

**Data and interface checks**

- Invalid inputs, prices, and missing required columns produce
  clear errors.
- Missing or duplicate RI components appear in the validation report.
- The documented No Upfront exception is handled explicitly.
- Every option has one comparable On-Demand price.
- Source version and publication date survive preparation and appear
  on screen.
- Rebuilding the processed table after a source refresh invalidates
  the processed-table cache.
- Changing runtime updates results without raw-file access.
- One-year and three-year sections use the same calculation definitions.
- No missing value is displayed as a zero price.
- No result claims to represent Riot's actual bill or recommends
  purchasing an RI.
