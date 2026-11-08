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

### CR-01: Runtime sensitivity and procurement constraints

- **From:** Team enhancement request, 2026-11-07
- **Part:** Decision support below the existing comparison
- **Evidence:** The starting UI accepts one runtime assumption and displays all payment options without budget or term constraints.
- **Change:** Add runtime sensitivity visualization, maximum-term/upfront filters and per-term comparison explanations.
- **Priority:** high
- **Status:** built in this enhanced ZIP; commit pending team integration


### CR-02: Make existing-coverage verification an explicit checkpoint

- **From:** Casey case contributor (submitted case), integrated 2026-11-08
- **Part:** Eligible-results summary and interpretation of savings
- **Evidence:** c6i.large, 100% runtime, maximum one year and $0 upfront yields $252.03/year savings against uncovered On-Demand ($744.60 versus $492.57). Casey assumes an existing matching All Upfront RI covers the whole horizon, with no other eligible use. A new RI then adds $492.57 of commitment rather than saving $252.03. The app already warns that coverage must be checked; it does not gather coverage status.
- **Change:** Add an explicit Uncovered / Covered / Not checked coverage checkpoint beside the summary. For Covered or Not checked, emphasize that displayed savings assume uncovered On-Demand usage and direct users to verify coverage and expiry. Preserve the existing price table and calculations; do not infer actual coverage or recommend a purchase.
- **Priority:** high
- **Acceptance:** All three answers preserve price values and eligibility. Covered/Not checked show the baseline warning. No answer is presented as account evidence or purchasing approval. Existing runtime, budget and term cases retain their results.
- **Status:** open — proposal only; not implemented

### CR-03: Compare finite workload horizons with full commitment obligations

- **From:** Maya case, submitted in Kelven's package; integrated 2026-11-08
- **Part:** Commitment-duration comparison for migrations and retiring workloads
- **Evidence:** One c6i.large runs continuously for 18 modeled months, with no existing coverage, reuse or resale. At recorded prices, one-year All Upfront plus six months On-Demand costs $832.30; three-year All Upfront creates a full $856 obligation, despite its lower $285.33 annualized price. The current app warns about different terms but has no project-horizon input.
- **Change:** Add an optional finite-horizon comparison alongside the constant-runtime view. Count every resulting RI obligation, including charges after demand ends; add an On-Demand remainder when a shorter RI expires. Clearly state constant future price, modeled-month, reuse and resale assumptions. Preserve existing tables and avoid claiming exhaustive purchasing optimization.
- **Priority:** medium
- **Acceptance:** The stated 18-month case reproduces $1,116.90 On-Demand, $832.30 one-year All Upfront plus remainder, and $856 three-year full obligation. Zero/invalid horizons are handled explicitly. Contract obligations are never prorated away when demand ends. Existing runtime/budget comparisons are unchanged.
- **Status:** open — proposal only; not implemented

### CR-04: Put the RI-only scope beside the shortlist verdict

- **From:** Priya Savings Plans versus RI case, 2026-11-08
- **Part:** The green eligible-option summary under `Plan within your constraints`
- **Evidence:** For `c6i.large`, 80% runtime, a one-year maximum term and $0 maximum upfront payment, the live app says the one-year No Upfront RI is the lowest modeled eligible option and saves $103.11 per modeled year. The app compares Standard RIs with On-Demand only. It has no Compute Savings Plan or EC2 Instance Savings Plan rows and no account-specific Savings Plans recommendation, although AWS documents that Compute Savings Plans can continue across instance-family and Region changes.
- **Change:** Put an RI-only scope statement immediately beside the green summary: this is the lowest eligible Standard RI in the current public-price model, not the best AWS purchase product. When flexibility across family or Region matters, direct the user to compare an account-specific Savings Plans recommendation and Engineering's future workload plan before approval.
- **Priority:** high
- **Acceptance:** The current RI and On-Demand numbers remain unchanged. Every positive shortlist summary names its RI-only scope. The app does not estimate Savings Plan savings without Savings Plan rates and account data. The next-action text points flexible-workload users to the missing account-specific comparison.
- **Status:** open — proposal only; not implemented

## Integration notes — 2026-11-08

- CR-01 is retained exactly as supplied, including its pending commit reference. Add the actual implementation commit after checking the team repository; this merge does not authenticate deployment history.
- Jordan, Alex and Winnie propose no additional request in their submitted current cases.
- An earlier validation draft proposed a downside-runtime summary as CR-02, but stated that it had not been appended to the shared log. The supplied current log contains only actual CR-01; the earlier draft proposal is not part of the latest submitted Alex case. The next available actual number is therefore used for Casey. If the live repository has acquired other requests since this supplied copy, merge and renumber these new entries before uploading; never overwrite or delete existing requests.
