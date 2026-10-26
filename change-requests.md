# Change requests

Our team's log of what we found and what should change, kept in the top folder of our team repo
from Module 9 to Module 13. Pull before you edit it and push soon after.

- For each finding, copy the request template below to the end of this file, give it the next
  number and fill in every field.
- Never delete a request. When it is built, set its status to `built` with the commit; when the
  team decides against it, `declined` with the reason.
- When this file gets long, ask Codex to move the built and declined requests into a dated file
  in `change-requests-archive/` (for example `change-requests-archive/2026-11-02.md`) and leave
  only the open ones here. Numbers continue; never reuse one.

Request template:

```markdown
### CR-NN: short title

- **From:** name, YYYY-MM-DD
- **Part:** the feature, number or function
- **Evidence:** what you did and saw: the input, what you expected, what the tool gave
- **Change:** what should change, in a sentence or two
- **Priority:** high, medium or low
- **Status:** open
```

A filled request (from the class lottery app):

```markdown
### CR-01: chance above 100% with two slots

- **From:** Ana, 2026-10-21
- **Part:** `odds` (the chance of selection by wage level)
- **Evidence:** one person at Level I and one at Level IV, two slots. Both must be selected,
  so each chance is 1. `odds` gave 0.4 and 1.6.
- **Change:** select each person at most once (without replacement), so no chance passes 1.
- **Priority:** high
- **Status:** open
```

## Requests

<!-- Add new requests below this comment, at the end of the file, newest last. -->

### CR-01: Make runtime assumptions understandable through visible hours-based feedback

- **From:** Ziling, 2026-10-24
- **Part:** Expected billable runtime input on the main dashboard; personal audit Part 1.
- **Evidence:** While using the app with c6i.16xlarge at 80% and 50%, I initially needed an additional explanation of expected billable runtime. The existing hover help distinguishes it from CPU utilization, but the meaning was not immediately clear to me. Treating CPU usage as runtime could materially change the cost comparison even when the chosen instance runs continuously.
- **Change:** Keep the current input and add a visible definition plus hours-based feedback tied to the selected percentage. For example, at 50%, show 4,380 modeled hours per year out of 8,760; explicitly explain that a continuously running instance has 100% runtime even at low CPU usage, and RI commitment charges remain payable when unused.
- **Priority:** medium
- **Status:** open

### CR-02: Show how purchase-option costs cross as expected runtime changes

- **From:** Ziling, 2026-10-24
- **Part:** Cost comparison presentation and scenario sensitivity; personal audit Part 1.
- **Evidence:** For c6i.16xlarge, changing runtime from 80% to 50% changes annual savings for the one-year No Upfront option from $3,300.07 to -$3,848.09, Partial Upfront from $4,050.19 to -$3,097.97, and All Upfront from $4,350.76 to -$2,797.40. The three-year options remain positive at 50%. The tables include signed values and comparison statuses, but I had to compare scenarios manually; the cost relationships across runtime levels are not visible together. These are observed app outputs from source version 20261012193925, not evidence of a calculation error.
- **Change:** Retain the exact-value tables and add a separate cost-versus-runtime chart for each commitment term. Show expected runtime from 0% to 100%, annual/annualized cost in USD, an On-Demand line and the available RI commitment-cost lines, their break-even crossings, and the selected-runtime marker. Use the existing calculator rather than a second formula implementation. Keep thresholds above 100% explicitly unattainable and do not combine different term totals into a best-plan ranking.
- **Priority:** medium
- **Status:** open

### CR-03: Require evidence before calling an instance engineering-approved

- **From:** Yihan, 2026-10-26
- **Part:** Instance-type selector and workload-fit handoff; personal audit Part 1.
- **Evidence:** I opened the professor build, selected `c6i.large`, and kept expected billable
  runtime at 80%. The selector offered nine values under the label "Engineering-approved
  instance type," but the app showed no engineering approval record, workload requirement,
  vCPU, memory, or performance-fit evidence. The page later stated that the tool does not assess
  instance performance requirements. The options are valid public-price C6i rows, but that alone
  does not establish engineering approval.
- **Change:** Treat the selector values as public-price instance types by default. Add an
  engineering-review input or data field that records an approved shortlist and its workload-fit
  basis, and show useful capacity context such as vCPU and memory. Only describe a size as
  engineering-approved when that evidence is present.
- **Priority:** high
- **Status:** open

### CR-04: Show full-term RI commitment cost beside annualized cost

- **From:** Yihan, 2026-10-26
- **Part:** Three-year cost table and commitment exposure; personal audit Part 2.
- **Evidence:** For `c6i.large` at 80% expected billable runtime, the three-year All Upfront row
  showed `$856.00` upfront, `$0` recurring RI per hour, and `$285.33` annualized RI cost. My
  independent Decimal calculation produced a full-term cost of `$856.00` and annualized cost of
  `$285.33`, so the app's number is correct. However, the table has no plainly labeled full-term
  RI cost for options that combine upfront and recurring charges; the manager must reconstruct
  the total obligation from separate columns.
- **Change:** Add a "Full-term RI commitment cost (USD)" column calculated as upfront payment
  plus recurring hourly charges across all term hours. Keep annualized RI cost for yearly
  comparison, but display both values and identify their periods so the total commitment is
  explicit.
- **Priority:** high
- **Status:** open

### CR-05: Allow a negotiated On-Demand rate in the comparison

- **From:** owendemian, 2026-10-26
- **Part:** Published-price cost comparison; individual audit Part 1.
- **Evidence:** In the professor build, `c6i.xlarge` at 70% expected billable runtime gives
  $1,042.44 annual On-Demand cost, $985.15 annualized cost for a one-year No Upfront RI,
  and $57.29 RI savings using the public $0.1700/hour On-Demand rate. An independent
  calculation with a **hypothetical**, not Riot-specific, 10% On-Demand discount gives
  $938.20 On-Demand cost and -$46.95 RI savings, reversing the lower-cost option. The app
  states that private discounts are excluded, so this is a decision-scope limitation,
  not an arithmetic error.
- **Change:** Add an optional user-entered effective On-Demand hourly rate, labeled as an
  internal assumption, while retaining the public rate as the default. Recalculate costs,
  savings, break-even runtime, and comparison status from the selected rate, and identify
  which rate was used in the result.
- **Priority:** medium
- **Status:** open

### CR-06: Expose an auditable calculation trace with unrounded rates

- **From:** owendemian, 2026-10-26
- **Part:** One-year RI comparison table and annualized cost; individual audit Part 2.
- **Evidence:** For `c6i.xlarge`, one-year No Upfront, the table displays recurring RI
  cost as $0.1125/hour and annualized RI cost as $985.15. Multiplying the displayed
  hourly rate by 8,760 gives $985.50. The committed price row for version
  `20261015191316` contains $0.1124600000/hour; independent hourly accumulation with
  that unrounded rate gives $985.15. The result is correct but cannot be reproduced
  from the displayed rate alone.
- **Change:** Provide an expandable or exportable calculation trace with the unrounded
  source rate, price-list version and option identifiers, modeled hours, formula, and
  rounding step for every financial result. Keep concise rounded values in the main
  table, but let a reviewer reproduce the reported total without inspecting source files.
- **Priority:** medium
- **Status:** open

