# RI Commitment Explorer

A single-page Streamlit planning tool for comparing On-Demand with one-year and three-year Standard Reserved Instances for one Linux C6i instance-equivalent in us-east-1. Select an engineering-approved instance type, then change expected billable runtime. Runtime is an editable assumption about hours needed, not CPU utilization.

## Live app

[Open RI Commitment Explorer](https://dso576-project-m10-dgvbvbjl9c4y23u6decrwc.streamlit.app/)

## Start from a fresh clone

Install Python 3.11+ and [uv](https://docs.astral.sh/uv/), then run these commands from the cloned repository folder.

macOS (zsh):

```zsh
uv run streamlit run dashboard.py
```

Windows (PowerShell):

```powershell
uv run streamlit run dashboard.py
```

No environment activation is needed. Stop the server with Ctrl+C. To run tests, use `uv run python -m pytest` on either system.

The committed price-options Parquet is sufficient to run the app. No AWS account, credentials, raw download, or preparation is needed at startup. For hosting, use `dashboard.py` as the entry point and install the dependencies in `pyproject.toml` with uv. Set `RI_PRICES_PATH` to override the default `data/processed/c6i_price_options.parquet`.

## Prepare or refresh

```bash
uv run python -m src.prepare_data
uv run python -m src.prepare_data --raw-path /path/to/ec2_us-east-1.csv
uv run python -m src.prepare_data --refresh
uv run pytest
```

Preparation searches the explicit path first, then `../dataset_aws-price-list/data/ec2_us-east-1.csv`, then `data/raw/ec2_us-east-1.csv`, and otherwise downloads the full regional AWS file. Paths are resolved from the project root. An explicit path must exist. The dataset repo's random samples are never used.

`--refresh` downloads the regional snapshot to `data/raw/ec2_us-east-1.csv` and uses it for that run. It cannot be combined with `--raw-path`. Neither the sibling dataset nor explicit input files are overwritten. Raw files and local environments are gitignored.

Preparation validates metadata/schema, filters rate components, pairs RI charges, and validates the final handoff before publishing. Failed runs exit nonzero, preserve published outputs, and write `data/processed/failed_report.json`. Successful runs remove a stale failure report. Files are staged and replaced atomically one at a time, with rollback on write exceptions; stop preparation before restarting an app to avoid observing a multi-file publication in progress. The runtime app reads only the final Parquet.

The checked-in snapshot has 54 options across nine instances, sourced from AWS publication 2026-10-15T19:13:16Z, version 20261015191316. These are published snapshot prices, not live prices.

## Main files

- `src/filter_rates.py`: fixed product scope, normalization, and invalid component records.
- `src/scenario.py`: one definition of financial measures, with Decimal precision 28.
- `src/pair_rates.py`: component pairing, On-Demand matching, ambiguity exclusions, reconciliation.
- `src/prepare_data.py`: source lookup, raw I/O, staging, publication, and reports.
- `src/load_data.py`: runtime Parquet contract validation without Streamlit.
- `src/views.py`: display formatting, handoff validation, separate term tables.
- `dashboard.py`: two session-state controls, cache keyed by path/mtime/size, orchestration.
- `tests/`: financial fixtures, synthetic data failures, source handling, loader/view contracts, and Streamlit interactions.
- `data/processed/filtering_report.json` and `validation_report.json`: source identity, actual counts, provenance, and findings.

Preparation also writes `c6i_filtered_rate_components.parquet`. It is a generated intermediate, gitignored because the app does not read it; the final price table and both reports are committed.

## Interpretation

RI charges are payable regardless of runtime. Annualized cost allocates the full commitment across its term; it is not a payment schedule. Upfront charges stay separate. Negative savings mean a modeled cost increase. Break-even can exceed 100% and is never clamped.

The model uses 8,760 hours per year, constant rates and runtime, and no time-value-of-money adjustment. It excludes private discounts, credits, actual usage, existing commitments, capital costs, workload changes, resale/exchange proceeds, storage, network, taxes, and other service charges. Annualization does not make one-year and three-year commitment risks equivalent.

The next action is to investigate expected runtime, commitments, and negotiated prices with internal data before a purchasing decision. The app does not establish Riot's actual costs or select an instance for performance.

## Enhanced version

Added maximum commitment term and upfront-budget filters, a separate eligible
shortlist, lowest modeled cost explanations within each term, and an interactive
runtime sensitivity chart. Dots show attainable break-even points; a dashed line
shows the entered runtime. Full original comparison tables remain above the
filtered analysis. No performance sizing or actual Riot usage is inferred.

Run with `uv run streamlit run dashboard.py`. Alternatively install
`python -m pip install -r requirements.txt`, then run
`python -m streamlit run dashboard.py`. Hosting entry point: `dashboard.py`.
The processed price snapshot is included. No AWS credentials are needed.

See `ENHANCEMENTS.md` for changes, validation scope, and verification status.
