# Team Vision: EC2 Commitment Planning for Riot Games

## Target user and decision

A FinOps Manager at Riot Games must decide whether a stable baseline of C6i/R6i compute capacity should remain On-Demand or use a 1-year or 3-year Reserved Instance with No Upfront, Partial Upfront, or All Upfront payment.

We aim to build a decision-support tool that compares these purchasing options for a specified baseline of EC2 capacity. It will show total modeled cost, upfront cash requirements, and break-even utilization under explicit assumptions so the manager can explain a purchasing recommendation.

Riot Games is the intended audience for this project. The stable C6i/R6i baseline is a project scenario supplied by the team, rather than a verified claim about Riot Games infrastructure or procurement practices.

## What decisions will the tool support?

For a baseline defined by instance type and size, instance count, region, operating system, tenancy, and expected usage, the manager can compare:

- Remaining on On-Demand pricing.
- A 1-year Reserved Instance with No Upfront, Partial Upfront, or All Upfront payment.
- A 3-year Reserved Instance with No Upfront, Partial Upfront, or All Upfront payment.

The tool will include only combinations supported by the price data and will label unavailable options. Comparisons will hold relevant product attributes and Reserved Instance offering class constant or make any differences explicit.

Costs will be compared over a common, stated horizon. A 1-year versus 3-year comparison must state the assumptions for any period after the 1-year contract expires; it will not silently assume future renewal prices. Reserved Instance estimates will include applicable upfront fees and recurring charges over the commitment term, including charges that remain when the modeled workload uses less capacity.

## What does the user care about?

- Total cost and modeled savings relative to On-Demand for equivalent capacity and a common horizon.
- Upfront cash requirements and the trade-off between payment timing and total cost.
- Break-even utilization or workload duration under the stated assumptions.
- The financial exposure if baseline demand falls or a workload ends before the commitment expires.
- Maintaining the required configuration and acknowledging any flexibility or coverage restrictions of the selected offering.
- Traceable price records, source dates, calculation assumptions, and a clear explanation of the recommendation.

## Usage scenarios

1. **Choose a commitment for a stable baseline.** The manager enters the baseline C6i/R6i configurations, instance counts, and expected usage, then compares On-Demand with available 1-year and 3-year Reserved Instance options.
2. **Compare payment choices.** For a selected term and configuration, the manager compares No Upfront, Partial Upfront, and All Upfront options to understand both total cost and initial cash requirements.
3. **Stress-test lower demand.** The manager evaluates lower-utilization and early-shutdown scenarios to see whether projected savings survive and how much commitment cost remains.
4. **Prepare an approval proposal.** The manager exports a comparison showing the proposed option, On-Demand baseline, modeled savings, upfront payment, break-even assumptions, and data limitations for finance and engineering review.

## Data and assumptions

The provided AWS price list dataset will supply public EC2 list prices, product attributes, and available Reserved Instance terms. Baseline capacity, expected usage, cash constraints, and workload duration must be supplied by the user or explicitly defined as scenarios; they are not observed in the price list.

The first version will focus on C6i and R6i and the supported regions and configurations in the dataset. Matching upfront and recurring price records, checking units, and confirming available term/payment combinations are required before calculating costs. List-price estimates are not actual Riot Games bills. Private discounts, credits, taxes, Spot prices, Savings Plans, and other infrastructure costs are outside the initial scope. Refunds, resale proceeds, and capacity-reservation benefits will not be assumed.

## Items to confirm during design analysis

- Which regions, instance sizes, operating systems, tenancy settings, and offering class should the first version support?
- What baseline instance counts and usage scenarios should be used for the demonstration?
- What common comparison horizon and post-expiration assumptions should be used?
- How should the manager express an upfront budget or preference for preserving cash?
