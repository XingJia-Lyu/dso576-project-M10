# Enhancements and verification

## Added behavior
- Inclusive upfront-budget and maximum-term filters for one instance-equivalent.
- Explicit no-eligible-RI state; On-Demand remains the baseline.
- Lowest modeled RI cost within each eligible term, including ties and negative savings.
- Runtime sensitivity chart from 0% to 100%, with exact model-derived data,
  break-even markers, current-runtime marker, and hover values.
- Full original tables remain visible; constraints apply only to the shortlist/chart.
- Original Decimal financial calculations and published snapshot are preserved.

## Verification performed
24 tests passed: existing financial scenario tests plus new non-UI decision tests.
Python syntax compilation passed. New tests check inclusive budget boundaries,
term filtering, empty eligibility, invalid budgets, independent hand calculations,
and chart-data agreement with current scenario costs.

The full Streamlit/PyArrow suite and live visual rendering were NOT run in the
editing environment because those packages were unavailable and package installation
failed. A Streamlit interaction test is included in tests/test_decision.py; existing
interface assertions were updated for the extra shortlist table.
Before recording or deployment, run `uv run python -m pytest` and
`uv run streamlit run dashboard.py` on a machine with the dependencies installed.
Check the chart, legend, zero-runtime state and budget/term controls.

## Validation report work still required
These enhancements do not replace the team's validation report. Support user needs
with research; show realistic live-app cases; independently verify important real
snapshot numbers; and explain what the tests guarantee and what remains outside
scope. Do not present synthetic test fixture prices as actual AWS snapshot prices.
No user research, deployment, or completed validation report is claimed here.

## Modeling limits
The upfront constraint is not a total-cost budget. It does not limit recurring
charges. Costs remain annualized and undiscounted, with constant rates/runtime.
One-year and three-year commitments are not interchangeable. This tool does not
model early termination, future workload changes, existing commitments or private
pricing. Results are conditional planning comparisons, not purchase instructions.

## Display update
Shortened metric values and placed hourly units in the label. Reduced metric font
size responsively. Primary comparison tables show five decision columns, with
On-Demand baseline above and hourly rates/status in expandable detail tables.
Shortlist headings are compact with explicit dollar/percentage units.
Horizontal scrolling may still be necessary on very narrow screens.
Syntax checked; visual rendering still requires local confirmation.
