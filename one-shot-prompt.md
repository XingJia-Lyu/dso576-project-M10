# RI Commitment Explorer — One-Shot Build Prompt

How to read this prompt: Vision and Design explain the product and
its reasoning. Pieces defines module boundaries. Details specifies
data rules, calculations, and interactions. Build order and Done when
define implementation and verification. This file is complete on its
own; it needs only the dataset repository and the public internet.

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
  -> filter_rates (Section B)
  -> c6i_filtered_rate_components.parquet + filtering_report.json
  -> pair_rates (Sections C–D)
  -> c6i_price_options.parquet + validation_report.json

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

4. **One definition per measure.** Financial formulas are defined once,
   in src/scenario.py. Preparation imports them; views only format
   and display their results.

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

| Piece | Job | Receives → returns | Never |
|---|---|---|---|
| src/prepare_data.py | Runs the two preparation stages in order; owns raw and intermediate file I/O, source metadata, and atomic writes | CLI arguments → files in data/processed/ | Computes formulas itself |
| src/filter_rates.py | Section B | raw rows + metadata → rate components + filtering findings | Pairs charges, computes costs, does file I/O |
| src/pair_rates.py | Sections C–D | rate components + invalid component records → price options + validation findings | Re-reads the raw CSV, does file I/O |
| src/load_data.py | Loader contract, Section D | processed-table path → validated price DataFrame | Imports Streamlit, rebuilds prices, computes scenarios |
| src/scenario.py | Formulas and scenario calculation, Section E | prices + instance + utilization → result table | Reads files, imports Streamlit, mutates input |
| src/views.py | Section F | result table + context → screen | Reads files, recomputes formulas |
| dashboard.py | Loads cached prices, draws the two controls, validates and converts inputs, calls the calculator, passes results to View | — | Parses prices, implements formulas |

## Details

### A. Data access and source metadata

The source is the full regional file in the dataset repository
USC-DSO-576-PS/dataset_aws-price-list, cloned beside this project:

../dataset_aws-price-list/data/ec2_us-east-1.csv

Resolve this path relative to the project root. Accept --raw-path
to override it; never hard-code a teammate's home directory. Use the
full file, never the repository's random sample.

If the source is missing, the preparation command may download it
from:

https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.csv

Never use the all-region EC2 URL.

Source lookup order: --raw-path; then the dataset-repository path above;
then data/raw/ec2_us-east-1.csv; otherwise download. Downloads and
--refresh write only to data/raw/ec2_us-east-1.csv (gitignored); a file
given with --raw-path or inside the dataset repository is never
overwritten.

When --refresh is passed, use the newly downloaded data/raw file
for that preparation run, overriding normal source lookup.
Reject combining --refresh with --raw-path.

Read the first five metadata lines and preserve Publication Date and
Version. Then read the data rows with:

```python
pd.read_csv(
    raw_path,
    skiprows=5,
    usecols=REQUIRED_COLUMNS,  # only the columns this prompt names; saves memory
    dtype=str,
    keep_default_na=False,  # "NA" in Pre Installed S/W is a real value
    low_memory=False,
)
```

Fail with an explanatory error if required metadata or columns
cannot be read.

The file is a price snapshot. Do not describe its prices as live or
imply that rows have distinct price-change dates.

Planning observations (record actual values in the reports on each
build; do not hard-code them): 393,649 rows, 93 columns, about 302.9 MB.

### B. Fixed scope, normalization, and rate checks

Keep a row only if it meets every scope condition:

```text
Product Family     = Compute Instance   (excludes c6i.metal, listed as
                                         "Compute Instance (bare metal)")
Region Code        = us-east-1
Operating System   = Linux
Tenancy            = Shared
CapacityStatus     = Used
Pre Installed S/W  = NA
MarketOption       = OnDemand
License Model      = No License required
Instance Type      starts with c6i.     (the dot excludes c6id, c6in)
```

Then keep these rate components:

- On-Demand: TermType = OnDemand and Unit = Hrs.
- Standard RI: TermType = Reserved, OfferingClass = standard
  (convertible RIs are out of scope), a canonical lease length, and
  Unit = Hrs or Quantity.

Trim surrounding whitespace, then map labels:

| Field | Accepted values | Canonical |
|---|---|---|
| LeaseContractLength | 1yr, 1 yr | term_years = 1 |
| LeaseContractLength | 3yr, 3 yr | term_years = 3 |
| PurchaseOption | No Upfront, NoUpfront | No Upfront |
| PurchaseOption | Partial Upfront, PartialUpfront | Partial Upfront |
| PurchaseOption | All Upfront, AllUpfront | All Upfront |

Lease and payment-label validation applies only to Reserved rows.
For On-Demand rows, set term_years and offering_class to null and
purchase_option to OnDemand; do not validate their source lease
or payment fields against the RI mapping table.

The spaced lease and unspaced payment forms are historical variants
kept for compatibility; they did not appear in the C6i snapshot checked
during planning. Any other value is an anomaly, never a guess.

Rate checks on every in-scope component:

- Currency = USD.
- PricePerUnit parses to a finite, nonnegative Decimal.
- Hrs components: StartingRange = 0 and EndingRange = Inf.
- Quantity components: require blank StartingRange and EndingRange
  (upfront charges have no rate range). Do not apply the Hrs range
  rule to them; report any nonblank range as an unsupported anomaly.

**Out of scope versus anomaly**

Scope is decided only by the product conditions, TermType
(OnDemand or Reserved), and OfferingClass (standard for Reserved).
Every other check applies to rows that pass them.

| Case | Action |
|---|---|
| Row fails a product condition, has another TermType, or is a Reserved row with OfferingClass other than standard | Exclude; count by reason in filtering_report.json |
| In-scope row with an unrecognized lease or payment label, a Unit other than Hrs (On-Demand) or Hrs/Quantity (Reserved), non-USD currency, invalid price, or unexpected range | Exclude the component; record (sku, offer_term_code, term_type, reason) in filtering_report.json; prepare_data passes these records to pairing |
| No comparable On-Demand component or no RI component remains | Stop preparation with a data-availability error |

Out-of-scope rows never stop the build.

**Filtered-component output**

Write one row per retained component to
data/processed/c6i_filtered_rate_components.parquet:

| Column | Type / meaning |
|---|---|
| price_list_version, publication_date | Source identity from metadata |
| sku, offer_term_code | String identifiers for pairing |
| instance_type | C6i configuration identifier |
| term_type | OnDemand or Reserved |
| term_years | Null for On-Demand; integer 1 or 3 for RI |
| purchase_option | OnDemand, No Upfront, Partial Upfront, or All Upfront |
| offering_class | Null for On-Demand; standard for RI |
| unit | Hrs or Quantity |
| price_per_unit_usd | Exact source decimal string |

filtering_report.json records source identity, input and retained
counts, retained instance types, scope exclusions summarized by
reason, and anomalies listed by rate key with reasons.

Planning check of the full file: 9 instance types and 54 Standard RI
groups in scope; all No Upfront groups have an Hrs component and no
Quantity component. Record actual counts on each build.

### C. Pairing and validation

One raw row is a price component, not a complete purchase option.

Pairing receives the invalid component records from Section B. An
anomalous component invalidates its RI group; never drop it and then
read its absence as a valid zero-upfront No Upfront option. An
anomalous On-Demand component invalidates every RI option on its SKU.

Group RI components by sku + offer_term_code. For each group:

- Require exactly one Hrs component; it is the recurring hourly rate.
- Partial Upfront and All Upfront: require exactly one Quantity
  component; it is the upfront payment.
- No Upfront: an absent Quantity component means zero upfront; a
  present one must also be zero.
- Accept a zero recurring hourly rate, as in valid All Upfront options.
- Require consistent configuration, term, and payment attributes
  within the group.

Match On-Demand by SKU: require exactly one On-Demand Hrs component
with the group's sku, and check that its instance_type matches the
group's. Zero or several matches make the option invalid. Never pick
the first, minimum, or average price.

If two valid groups share one instance/term/payment combination,
exclude that combination and report the ambiguity.

Exclude invalid options and record their keys and reasons. Never fill
a missing price with zero.

validation_report.json includes:

- Source file, publication date, and version.
- Raw row count and retained component counts.
- Valid option counts by instance, term, and payment option.
- Invalid or unmatched keys and exclusion reasons.
- Output row count and file size (write the Parquet first).

Publish results only after both stages succeed. If either stage fails,
including when no valid options remain, keep the last published files
in data/processed/ unchanged, write data/processed/failed_report.json
with the reason and findings, and exit with a nonzero status.

### D. Processed price contract and Loader

data/processed/c6i_price_options.parquet has one row per valid
Standard RI option:

| Column | Meaning |
|---|---|
| price_list_version | Source version |
| publication_date | Source publication date |
| instance_type | Selected EC2 configuration identifier |
| term_years | Integer 1 or 3 |
| purchase_option | Canonical payment label |
| offering_class | standard |
| on_demand_hourly_usd | Comparable On-Demand hourly rate |
| ri_upfront_usd | Upfront payment |
| ri_hourly_usd | Recurring committed hourly rate |
| effective_ri_hourly_usd | Full-term normalized RI rate, for display |

Monetary fields are decimal strings. Source components keep their exact
values; effective_ri_hourly_usd is str() of the Section E result computed
with 28-digit precision. Convert to Decimal directly, never through a
float. SKU and offer-term provenance stays in the reports; extra
provenance columns must not change this contract.

**Loader contract**

```python
from pathlib import Path
import pandas as pd

def load_price_options(path: Path) -> pd.DataFrame: ...
```

It is the only runtime piece that opens the processed file. It checks:

- The file exists and has every column above.
- Exactly one price_list_version and one publication_date.
- term_years in {1, 3}; purchase_option canonical; offering_class standard.
- Monetary strings parse to finite, nonnegative Decimals;
  on_demand_hourly_usd > 0.
- Each instance/term/payment combination appears once.

It returns the table as stored, with monetary fields as strings. On any
failure it raises ProcessedDataError telling the user to run
`uv run python -m src.prepare_data`. It never falls back to the sample
or invented prices. It does not import Streamlit, so it is tested alone.

### E. Formulas and scenario calculation

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

Utilization is expected billable runtime: 0.80 means capacity is needed
for 80% of modeled term hours. It is not CPU utilization; a machine
running continuously at low CPU gets no On-Demand price reduction.

Reject non-finite inputs and values outside 0–1. Require a positive
On-Demand hourly price.

**Definitions (src/scenario.py; pair_rates imports them)**

```text
T = 8760 * term_years
p = on_demand_hourly_usd
h = ri_hourly_usd
F = ri_upfront_usd
u = utilization

ri_term_cost            = F + h * T          # from components
od_term_cost            = p * u * T
term_savings            = od_term_cost - ri_term_cost

effective_ri_hourly     = ri_term_cost / T   # preparation; display only
ri_annualized_cost      = ri_term_cost / term_years
on_demand_annual_cost   = od_term_cost / term_years
annual_savings_vs_od    = term_savings / term_years
break_even_utilization  = ri_term_cost / (p * T)
```

Cost, savings, break-even, and status always come from F, h, and p.
The stored effective_ri_hourly_usd is passed through for display and
never multiplied back, because a non-terminating division would make
the result depend on stored precision.

Use Decimal arithmetic with at least 28 digits. Do not round
intermediate results for display.

Classify from unrounded term_savings:

```text
positive -> RI lower modeled cost
zero     -> Break-even
negative -> On-Demand lower modeled cost
```

Return the prepared fields for the selected instance, monetary strings
converted to Decimal, plus:

```text
ri_annualized_cost_usd
on_demand_annual_cost_usd
annual_savings_vs_od_usd
break_even_utilization
comparison_status
```

Return an empty table with the same schema when the instance has no
valid options. Do not mutate the input.

### F. View and interaction

```python
def render_comparison(
    results: pd.DataFrame,
    instance_type: str,
    utilization: Decimal,
) -> None: ...
```

**First load**

- Show the product title and the Section B scope (us-east-1, Linux,
  Shared tenancy, Used capacity, no pre-installed software,
  non-bare-metal C6i) as information, not controls.
- Instance select starts unselected and offers only instances in the
  validated table.
- Runtime is a number input labeled “Expected billable runtime (%)”,
  0–100, step 1, default 80, marked as an editable assumption. Its help
  text explains runtime versus CPU utilization.
- Calculate only when both inputs are valid. Dashboard converts input
  with `Decimal(str(runtime_percent)) / Decimal("100")`.

**Who handles which state**

| State | Owner | Shows |
|---|---|---|
| No instance selected | Dashboard | “Select an instance type to compare purchase options.” |
| Invalid runtime | Dashboard | Input error; no calculation |
| Processed file missing or invalid | Loader raises ProcessedDataError; Dashboard catches it | Instruction to run preparation |
| Empty result table | View | “No valid Reserved Instance options are available for this selection.” |
| One term has no options | View | That term's section says no valid options are available |
| Missing columns, rows for another instance, mixed source metadata | View | Handoff error; no partial table |

**Results**

Show the selected instance, expected runtime, matching On-Demand hourly
rate, and source publication date and version. Then separate one-year
and three-year sections, rows ordered No Upfront, Partial Upfront,
All Upfront, with:

- Purchase option, upfront payment, recurring RI hourly rate,
  effective RI hourly cost.
- Annualized RI cost, On-Demand annual cost at the entered runtime,
  annual savings versus On-Demand.
- Break-even runtime and comparison status.

Display rules (formatting never affects calculation or status; build a
separate display table and leave the input unchanged):

- Annual and upfront amounts in USD to two decimals.
- Hourly rates with enough precision that a nonzero rate never shows as
  zero; a true zero recurring rate is shown as zero.
- Runtime and break-even as percentages, with extra precision when
  needed so the displayed break-even agrees with the status.
- Negative savings stay signed and are explained as a modeled cost
  increase.
- Break-even above 100% is shown unclamped and explained as
  unattainable within the modeled runtime range.
- Annualized cost is labeled as an allocation across the term, not an
  annual payment schedule; upfront payment stays a separate column.
- Missing values are never shown as zero prices.

Do not rank one-year against three-year plans or name an unconditional
“best plan.” Present cost and duration together.

Limitation notice: results are scenarios on an AWS published price
snapshot, excluding Riot's private discounts, credits, actual usage,
existing commitments, capital costs, and future workload changes.
Next action: validate expected runtime, existing commitments, and
negotiated pricing with internal data before any purchasing decision.

A chart is optional; the comparison table is required. Styling and
minor wording are left to the builder.

### G. Environment, caching, and deployment

| Tool | Job | Why |
|---|---|---|
| pandas | Preparation and small-table selection | The processed table is small; SQL adds nothing |
| pyarrow | Parquet | Typed, compact handoff files |
| decimal | Financial arithmetic | No float rounding in money |
| Streamlit | Interface | Single page, two inputs |
| pytest | Calculation and data-validation tests | Pieces checked alone |

The raw CSV is read only during preparation and never held by the app.

Create an independent uv project (requires-python >= 3.11) with
pyproject.toml and uv.lock:

```bash
uv sync
uv run python -m src.prepare_data
uv run python -m src.prepare_data --raw-path /path/to/ec2_us-east-1.csv
uv run python -m src.prepare_data --refresh
uv run streamlit run dashboard.py
uv run pytest
```

dashboard.py wraps load_price_options in st.cache_data keyed on the
path, modification time, and size, so replacing the file invalidates
the cache. Interactions never open raw data or write files. Inputs live
in session state; persistence between visits is not required.

The processed-table path defaults to
data/processed/c6i_price_options.parquet and can be overridden with the
RI_PRICES_PATH environment variable. For cloud deployment, commit the
processed table and reports, deploy the app with that path, and never
download or parse raw AWS data at startup.

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

data/raw/ (downloads), local environments, and caches stay out of Git.

## Build order

1. Read the full regional file and validate metadata and schema.
2. Implement Section B; write the component table and filtering report.
3. Implement the Section E formulas, then Section C pairing; write the
   price-option table and validation report.
4. Implement calculate_scenario and check the fixtures below.
5. Build Loader and View against their contracts.
6. Connect controls and walk through each Vision scenario.
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

At 60%, savings must be zero and status Break-even.
At 50%, savings must be -$175.20 and status On-Demand lower modeled cost.

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

The View shows the full $1,576.80 upfront payment separately from the
$525.60 annualized cost.

**Calculation fixture: break-even above 100%**

One-year No Upfront, On-Demand $0.20/h, RI $0.25/h: break-even 125%,
shown unclamped and explained as unattainable; status On-Demand lower
modeled cost at any runtime.

**More calculation tests**

Invented No Upfront, Partial Upfront, and All Upfront options for both
terms: independently verify effective rates, annualized costs,
break-even, and savings signs.

**Data tests (tiny invented tables)**

- Missing Hrs, duplicate Hrs, duplicate Quantity, missing required
  upfront, nonzero No Upfront Quantity: each excluded and reported.
- No On-Demand row for the SKU, or two: excluded and reported.
- Quantity component with blank ranges: kept. Hrs component with an
  unexpected range, or Quantity component with a nonblank range: its
  option is invalid and reported.
- No Upfront group whose Quantity component is anomalous: the option
  is invalid, not treated as zero upfront.
- Row with another MarketOption: counted as a scope exclusion; the
  build continues.
- Unknown lease or payment label: reported, not guessed.
- Two valid groups for one instance/term/payment: combination excluded.

**Data and interface checks**

- Independently reconcile candidate RI groups with accepted and
  rejected groups: candidates = valid + rejected, with every rejection
  carrying a reason. Verify the valid output count against groups that
  pass pairing, On-Demand matching, and uniqueness checks; do not
  require equality with an unvalidated distinct count of raw rows.
- Source version and publication date survive preparation and appear
  on screen.
- Loader rejects a file with a missing column or mixed versions, with
  the preparation instruction.
- Replacing the processed table invalidates the cache.
- Changing runtime updates results without raw-file access.
- One-year and three-year sections use the same definitions; an empty
  term shows its own message.
- View leaves its input table unchanged and shows a handoff error for
  missing columns.
- No missing value is displayed as a zero price.
- No result claims to represent Riot's actual bill or recommends
  purchasing an RI.
