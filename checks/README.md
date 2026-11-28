# R5: independent verification from the original AWS file

The reference script `check_original_prices.py` scans the **entire original publisher CSV** before reading separately recorded app observations. It does not import `src`, pandas, Streamlit, or the collector. Its expected prices and financial results come from the original file, with exact `Fraction` arithmetic. It never starts from displayed totals or manually copied rates.

`capture_app_results.py` is the observation side only. It calls the checked-out app's actual loader, scenario and decision functions, and uses local Streamlit AppTest to collect displayed tables, conditional messages, and the actual serialized chart datasets. **This collector is not the independent reference.** Both files are committed so either side can be inspected and rerun.

## Rerun from the repository root

Python 3.11+ and uv are required. Run one command at a time on macOS or Windows:

```text
uv sync --frozen
uv run python checks/check_original_prices.py --download --download-only --source-version 20261015191316 --raw data/raw/ec2_us-east-1_20261015191316.csv
uv run python checks/capture_app_results.py
uv run python checks/check_original_prices.py --source-version 20261015191316 --raw data/raw/ec2_us-east-1_20261015191316.csv --observed checks/r5-observed.json.gz
uv run python -m pytest tests/test_original_price_audit.py -q
```

The first source download is about 289 MiB. AWS requires no account for this public URL:

https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20261015191316/us-east-1/index.csv

The raw file stays gitignored. The downloader records its actual retrieval time, URL, size and SHA-256 in the adjacent `.receipt.json`; an existing file is never overwritten. A file without a matching receipt is rejected. The pinned file is version `20261015191316`, published `2026-10-15T19:13:16Z`. The observed table uses this same version. The first recorded download was at `2026-11-28T02:07:01.035798+00:00`; this is not its publication date.

## Recorded scope and output

The run inspected 393,649 data rows and 93 columns, retaining 99 comparable rate components and reconstructing all 54 Standard RI options across nine instance types. The expected option set is derived from the raw CSV, not hard-coded as 54. A missing, extra or duplicate app option fails reconciliation.

```text
Source version: 20261015191316; 393,649 original rows
Options independently reconstructed: 54
Recorded checks: 329862; mismatches: 0
Coverage: {"constraints": 648, "scenarios": 5454, "sensitivity": 5454, "ui": 648}
PASS
```

Coverage:

- All 162 raw price inputs (matching On-Demand, upfront and recurring RI), plus 54 stored effective rates; exact option-set and snapshot checks.
- 54 options × 101 integer runtimes = 5,454 scenario rows. Each checks RI annual cost, On-Demand annual cost, annual savings, break-even and sign/status.
- 5,454 sensitivity-helper rows; both cost series checked.
- 648 constraint selections: every instance at 0/50/80/100%, both maximum terms, every unique source-derived upfront amount and one cent below each positive boundary, plus zero. Eligible option sets must match exactly, with no duplicates.
- 648 local displayed states: every instance at 0/50/80/100%, both maximum terms, and every declared upfront budget boundary. Each widget value is explicitly set. Displayed annual amounts/status, shortlist membership and per-term cheapest eligible options/messages are checked.
- Actual chart line costs and full integer-grid coverage; attainable break-even dots; the entered-runtime marker and coordinate fields in those 648 states. Float chart coordinates tolerate at most $0.00000001 or 0.00000001 percentage points.

Financial reference comparisons tolerate only 1e-20 absolute units (stored effective rates: 1e-24) to accommodate the app's 28-digit Decimal division. Displayed dollar strings match exactly, including negative amounts. Equality/status and option membership are exact. These tolerances are substantially below a cent; they are not an allowed business discrepancy.

## Evidence files

- `r5-observed.json.gz`: actual captured app outputs, app commit, app source hashes, prepared-file hash and capture time.
- `r5-results/summary.json`: source identity/hash, actual download receipt, coverage and mismatches.
- `r5-results/comparisons.csv.gz`: every expected/observed comparison, field, selection and pass flag.
- `r5-results/original-records.csv`: all 99 selected original records, preserving every CSV field value. It is regenerated from the full source on every check, never used as the reference input.
- `r5-results/original_options.json`: original SKU, offer-term code, RateCodes and one-based data-record numbers for every option, plus independently read rates. Record numbers exclude the five metadata rows and header.
- `r5-results/acceptance-run.txt`: complete final checker stdout. Earlier 18-state development output is kept separately, with its earlier coverage clearly named.
- `r5-results/pytest-final.txt`: complete final pytest stdout, including the legacy skip.

The checked app base was `066fceff8b4af0ce89f3bb309a9ed997e275fb5c`. New R5 files do not change its calculations or display. The collector also stores each `src/*.py` and `dashboard.py` hash so a dirty working tree is not hidden behind a commit name.

## Future price updates

Download a **new versioned filename** with the new `--source-version` first. Prepare the app table from that exact source using its normal preparation command, then recapture observations and run the independent checker against the same version. Do not reuse old observations or relabel an old receipt. Counts and budget boundaries are derived afresh. A changed schema, unsupported rate dimension or ambiguous group fails explicitly rather than silently treating missing charges as zero. Review the failure before changing scope.

Exit codes: `0` = declared comparison passed, `1` = mismatched app results, `2` = invalid/unavailable source or evidence. The reference reads original rows first; it does not derive truth from the prepared table.

## Limits

This verifies the declared local app version and public-price model, not the identity of the live deployment, browser rendering, negotiated company costs or actual savings. It covers every current integer runtime in the calculation layer, but only the declared constraint boundaries and 648 displayed interaction states. Future main results (for example a new planning-horizon model) require extending this checker; the current audit does not imply coverage for them. Existing commitments and workload suitability still need separate business evidence.
