# Build report

Status: complete

- Builder model(s): Codex GPT-6.1 (gpt-6.1-sol), medium reasoning. (Coordinator: corrected from "Codex (GPT-6)".)
- Dates and sessions: 2026-10-19, one build session.
- App repo: USC-DSO-576-PS/project-prof-build-M10
- Run command (from a fresh clone): first `uv sync --locked`, then macOS (zsh): `.venv/bin/python -m streamlit run dashboard.py`; Windows (PowerShell): `.\.venv\Scripts\python.exe -m streamlit run dashboard.py`. To regenerate on either system: `uv run python -m src.prepare_data`.

## Outcome

Built the specified single-page Streamlit app, preparation pipeline, validated Decimal price contract, comparison tables, and test suite. The real full regional snapshot produces 99 retained components, nine C6i instances, and 54 valid Standard RI options, with zero anomalies and zero rejected groups. Both terms show separate upfront, hourly, annualized cost, savings, break-even, and status. Runtime changes use cached processed prices. No raw data is read by the app. Automated Streamlit walkthroughs and an actual HTTP startup pass; final fresh-clone verification is recorded below.

## Asked or guessed

No questions were asked, as instructed.

| # | Prompt text (quote, with section) | What the builder did | Effect on the app | Cause (PROMPT / BUILD / UNSURE) |
|---|---|---|---|---|
| 1 | A: “If the source is missing, the preparation command may download it” | The sibling repo contained only samples and documentation. Downloaded the permitted full regional AWS URL into data/raw/. | Uses full real snapshot; never samples. | PROMPT (coordinator confirmed: the dataset repo gitignores data/ and ships the full CSV only via its download_data.py, so the prompt's "full regional file in the dataset repository" path does not exist in a plain clone; the prompt's own download fallback resolved it with no effect on the app) |
| 2 | F: “Styling and minor wording are left to the builder.” | Used a light background, navy headings, three context metrics, two term tables, and a visible assumptions notice. | Same specified two controls and measures; no ranking or added dashboard. | PROMPT |
| 3 | B: “Exclude; count by reason” | Assign each scope exclusion to its first failed condition, in displayed filter order; record the policy in filtering_report.json. | Counts are mutually exclusive and reconcile with input rows. | PROMPT |
| 4 | User: “Commit ... only the condensed data files the app reads”; G: “commit the processed table and reports” | Commit the final 54-row price table and both reports. Generate the 99-row filtered component Parquet during preparation, but gitignore it. | App starts from committed data; intermediate remains reproducible. | BUILD (coordinator retag: the "commit only the condensed data files" rule comes from the build protocol, not the prompt; the prompt's folder structure lists c6i_filtered_rate_components.parquet under data/processed/. App unaffected; preparation regenerates it.) |
| 5 | C: “Publish results only after both stages succeed”; Pieces: “atomic writes” | Stage and validate all outputs before per-file atomic replacement, with rollback on write exceptions. No cross-file reader transaction is added. | Failed preparation preserves prior outputs; app reads only one published price file. README notes multi-file publication is not globally atomic. | PROMPT |
| 6 | F: “with extra precision when needed so the displayed break-even agrees with the status” | Increase break-even percentage decimal places until the displayed threshold preserves its relation to the entered runtime. | A near-threshold value does not round into a misleading equality. | PROMPT |
| 7 | C: “Source file, publication date, and version.”; no required path representation | Store source paths relative to the project root, including relative sibling paths for external sources. | Portable provenance without a hard-coded home path. | PROMPT |
| 8 | A: “Accept --raw-path to override it” | Treat an explicit nonexistent path as an error instead of silently falling back. | Typographical input-path errors remain visible with a failed report. | PROMPT |

## Use cases

| # | Use case | Result (works / partly / fails) | Cause (PROMPT / BUILD / UNSURE / —) | Evidence |
|---|---|---|---|---|
| 1 | Select an engineering-approved C6i instance and inspect Standard RI options beside On-Demand | works | — | AppTest starts unselected; c6i.large exposes two term tables with three payment options each and the matching OD rate. Additional c6i.32xlarge walkthrough passes. |
| 2 | Lower expected runtime and see options lose modeled savings | works | — | Real snapshot at 10% runtime shows all six options as On-Demand lower modeled cost with negative savings. Fixture at 80%, 60%, 50% gives +350.40, 0, -175.20. |
| 3 | Review break-even threshold and commitment duration before internal investigation | works | — | Separate one-/three-year sections show thresholds and full upfront amounts; annualization notice, assumptions, and internal-data next action remain visible. Fixture 125% threshold is unclamped with an unattainable notice. |

## The prompt's "done when" checks

| Check | Result | Note |
|---|---|---|
| Fresh clone can prepare and run using documented dependencies | pass | Local Git clone under $TMPDIR; uv sync --locked; default preparation downloaded full regional source and reproduced identical committed outputs; 60 tests passed in 17.93s; AppTest rendered both term tables; real HTTP startup passed and server stopped. |
| One-year No Upfront fixture at 80% | pass | Effective .12, RI 1051.20, OD 1401.60, savings 350.40, break-even 60%, RI lower status. |
| One-year fixture at 60% and 50% | pass | Exactly zero / Break-even and -175.20 / On-Demand lower. |
| Three-year All Upfront fixture | pass | Effective .06, annualized 525.60, OD 1401.60, savings 876.00, threshold 30%; view separately shows full 1576.80 upfront. |
| Break-even above 100% | pass | 125.00% displayed unclamped; unattainable notice and On-Demand lower status. |
| Invented options for all three payments and both terms | pass | Independent component arithmetic checks at 0%, 50%, 100%; stored effective rate is deliberately wrong in one fixture to verify it never drives cost. |
| Missing/duplicate Hrs; duplicate Quantity; missing upfront; nonzero No Upfront Quantity | pass | Each excluded with a nonempty rejection reason. |
| Missing or duplicate On-Demand; configuration mismatch | pass | Excluded and reported; no arbitrary price selection. |
| Blank Quantity ranges; anomalous Hrs/Quantity ranges | pass | Blank upfront ranges retained; unsupported ranges invalidate their group. |
| Anomalous No Upfront Quantity | pass | Group invalidated; never interpreted as absent zero upfront. |
| Other MarketOption excluded without stopping | pass | Tiny fixture counts Spot as a scope exclusion and retains valid option. |
| Unknown lease/payment; historical variants | pass | Unknown labels reported; whitespace and accepted historical variants normalize; OD lease/payment ignored. |
| Ambiguous instance/term/payment combination | pass | Both candidate groups excluded and reported. |
| Independent candidate reconciliation | pass | Explicit raw scope selection independently reconstructs candidate keys; candidate set equals disjoint accepted plus rejected sets. Actual 54 = 54 + 0. Accepted group components, OD matching, and output uniqueness checked. |
| Source version/date survive and appear on screen | pass | 20261015191316 / 2026-10-15T19:13:16Z in both reports, price table, and tested view caption. |
| Loader missing column/mixed versions | pass | ProcessedDataError includes exact preparation instruction; also rejects null/invalid money, duplicate options, zero OD, invalid term/payment, and missing file. |
| Cache invalidated on replacement | pass | Instrumented loader called once across interactions, then again after changed mtime/size. |
| Runtime changes do not access raw data | pass | AppTest replaces pd.read_csv with a function that raises; input changes and calculations still pass. |
| Same definitions across terms; empty term | pass | Shared scenario function; view tests assert per-term empty message. |
| View input unchanged; missing columns handoff error | pass | DataFrame equality before/after; invalid handoff shows error and no partial table. Also tests wrong instance, mixed metadata, and null values. |
| No missing prices shown as zero | pass | Loader and view reject missing values. True recurring zero displays $0; tiny nonzero hourly rate stays nonzero. |
| No actual Riot bill or RI purchase recommendation | pass | Visible hypothetical context, runtime assumption, limitations, and “investigate with internal data”; no best-plan ranking. |
| Preparation failure preserves last outputs | pass | Malformed raw input, missing comparable components, and no valid paired option leave published sentinel files unchanged and write failed_report.json. |
| Refresh / source lookup safety | pass | Explicit path > sibling > local source; mocked refresh selects new local download without modifying sibling/explicit sources; incompatible flags rejected. Actual regional download succeeded during build. |
| Automated suite | pass | 60 tests including full-source reconciliation, financial fixtures, data validation, and Streamlit AppTest. |
| Actual server startup | pass | Free port 46875; health endpoint ok, homepage HTTP 200 in 2.12 seconds; server terminated afterward. |

## Real-world operation

- Data size used (rows, MB) and whether it is the full real size: Full regional CSV, 393,649 data rows, 93 columns, 302,869,403 bytes (302.869 MB decimal). Not the repository sample.
- Start-up time: Streamlit AppTest first render 0.639 seconds; actual server health/homepage ready in 2.12 seconds. Preparation 6.77 seconds on a warm filesystem (separate earlier run 8.52 seconds).
- Slowest interaction, and how slow: 0.0304 seconds for c6i.large selection in the measured AppTest walkthrough; runtime updates 0.0248–0.0292 seconds. These measure local script execution, not browser network/render latency.
- Memory at peak: AppTest process 171,788 KiB (~167.8 MiB); full preparation process 1,025,444 KiB (~1001 MiB). No persistent server left running.

## Data

- Raw source: https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.csv ; downloaded to data/raw/ec2_us-east-1.csv because sibling full CSV was absent. Publication 2026-10-15T19:13:16Z; version 20261015191316.
- Condensed files committed (name, rows, MB): c6i_price_options.parquet, 54 rows, 8,479 bytes (0.008479 MB). filtering_report.json, 5,511 bytes (0.005511 MB); validation_report.json, 17,746 bytes (0.017746 MB). Reports describe 99 retained components, 90 Reserved + 9 OnDemand, nine instances, 54 candidate/accepted groups, zero rejected groups/anomalies. Generated uncommitted filtered component Parquet: 99 rows, 8,371 bytes.
- `data/raw/` deleted: no. Retained locally as instructed, gitignored and excluded from commits.

## Build problems not caused by the prompt

- Portability fix (2026-10-20): BUILD — no app, test, dependency, or data change needed. App/test imports use cross-platform APIs, paths use pathlib/os.path, and Git tracks no symbolic links. README now gives separate macOS (zsh) and Windows (PowerShell) install/run commands using the Python Streamlit entry point, plus test and stop instructions. No recorded Linux-only implementation choice needed retagging; Linux in the product scope describes AWS prices, not the host OS. No prompt requirement needed a platform substitute.
- Initial AppTest helper passed arguments to run() instead of from_function(); corrected and all interface tests pass.
- One editing command used bare python, which this environment does not provide. Reissued with uv run python; no artifact damage.
- uv could not hardlink across filesystems and copied cached dependencies instead; installation completed.
- No external account, private data, or additional service was needed.
- Fresh-clone verification completed: locked dependency install, default public download/preparation, all 60 tests, Streamlit selection walkthrough, and real HTTP server startup passed. Regenerated tracked data/reports matched the committed files with a clean Git status. Scratch clone and logs live under $TMPDIR.
- Delivery: code, preparation, lockfile, runtime price table, reports, and unchanged one-shot-prompt.md are committed on main; origin main is the requested push destination.

## Coordinator

- Fresh clone starts: yes. Cloned from GitHub to a scratch folder; `uv sync --locked` then `uv run streamlit run dashboard.py` on port 8641: health endpoint ok, homepage HTTP 200; server stopped. AppTest first render: title, fixed-scope caption, unselected instance select over the 9 validated C6i types, runtime default 80, "Select an instance type to compare purchase options." `uv run pytest`: 59 passed, 1 skipped (the full-source reconciliation test skips when data/raw/ is absent, as in a fresh clone; the builder ran it with the raw file). `uv run python -m src.prepare_data --raw-path <builder's downloaded CSV>`: 54 options from 393,649 rows in 5.2 s, about 1.0 GB peak; c6i_price_options.parquet byte-identical to the committed one (reports differed only in the source_file path); changes reverted.
- Data size: the build used the full us-east-1 regional CSV (393,649 data rows, 93 columns, 302,869,403 bytes, version 20261015191316), which matches the prompt's planning figures (393,649 rows, 93 columns, about 302.9 MB). Not the sample. Source came from the prompt's permitted AWS URL because the sibling dataset clone has no data/ folder.
- Use cases re-walked: 3/3 work. (1) c6i.xlarge at 80%: OD $0.1700/h shown with publication date and version; one-year and three-year tables with No/Partial/All Upfront; every annualized cost, break-even and savings figure matched my independent Decimal recomputation from the parquet (e.g. 1-yr No Upfront $985.15, break-even 66.15%, savings $206.21). (2) Runtime lowered to 40%: all one-year options and 3-yr No/Partial Upfront flip to "On-Demand lower modeled cost" with signed negative savings and the cost-increase note; 3-yr All Upfront (break-even 38.32%) stays RI lower at +$25.01, matching my numbers. (3) Break-even and duration: separate term sections, full upfront shown apart from annualized cost with the allocation caption, term-risk notice, limitation notice and "investigate with internal data" next action; no best-plan ranking.
- Causes corrected (and why): Asked-or-guessed #4 retagged PROMPT -> BUILD (the instruction to commit only condensed files is a build-protocol rule; the prompt's folder structure includes the filtered-component parquet). #1 kept PROMPT with the reason clarified (prompt names a dataset-repo path that a plain clone does not contain). Builder model line corrected. Other entries agree with my walk-through.
- No raw data, secrets or identifiers; size limits met: yes. data/raw/ is gitignored and absent from git; no CSV in git; no secrets/tokens or student names, emails or IDs found (only commit author is Peng Shi); largest tracked file uv.lock 308 KB; pack 135 KiB. one-shot-prompt.md is byte-identical to the workspace copy; change-requests.md added unchanged.
- Build setup: the dataset repo was cloned as the sibling `../dataset_aws-price-list` the prompt names, but a plain clone of it has no `data/` folder (the full CSV comes only from its `download_data.py`), so the preparation command used the prompt's download fallback (Asked-or-guessed #1). The build protocol's rule to commit only the condensed files the app reads is why the filtered-component Parquet is regenerated rather than committed (#4).
- Cross-platform pass (2026-10-20): a separate session reviewed the app for Linux-only code. None was found: imports are standard cross-platform modules plus pandas/streamlit/pytest, paths use pathlib, and Git tracks no symbolic links. No app, test, dependency or data change was needed; the README now gives separate macOS (zsh) and Windows (PowerShell) install, run, test and stop commands. Verified on Linux from a `git -c core.symlinks=false` clone (as Windows checks out): `uv sync --locked`, 59 passed and 1 skipped, and the macOS-style command started the app (health ok, HTTP 200). Native macOS and Windows runs were not done by the coordinator.
