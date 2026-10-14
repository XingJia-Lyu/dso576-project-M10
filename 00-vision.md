# Vision: RI Commitment Explorer

## Audience and decision

RI Commitment Explorer serves a FinOps manager at Riot Games who is evaluating how to buy a stable baseline of Linux C6i compute capacity in `us-east-1`. For one selected C6i instance type, the manager needs to decide whether the public On-Demand price or one of the available one-year and three-year Standard Reserved Instance (RI) payment options is the more economical public-price starting point at an assumed utilization level. The tool supports a pricing scenario, not an automated purchase decision.

## Why this tool

Today, the manager can compare AWS pricing pages and calculate commitment economics by hand, or consult account-specific tools such as Cost Explorer. Manual comparison is slow because RI charges may be split between upfront and recurring components, and it is hard to see how a changed utilization assumption changes the result. Cost Explorer is valuable when internal account history is available, but it is not a transparent public-price scenario tool. RI Commitment Explorer puts the comparable public options, assumptions, and calculations in one auditable view. It complements rather than replaces an internal usage-and-billing review.

## What the manager needs to see

The manager cares about estimated cost under a stated utilization assumption, the savings or extra cost versus On-Demand, the break-even utilization at which each RI becomes economical, the upfront payment required by each option, and the risk of committing for three years when game demand may change. Every result must retain the AWS price-list version and state that list prices are not Riot's actual bill: private discounts, credits, existing commitments, Savings Plans, workload performance, and real demand are outside this tool.

## Concrete use cases

- The manager selects a Linux C6i instance type and an assumed utilization level. The tool shows the matching On-Demand rate alongside every available one-year and three-year Standard RI payment option, with estimated cost, savings versus On-Demand, upfront payment, and break-even utilization. The manager decides which option, if any, deserves an internal usage and billing-data review.
- Before a launch or renewal, the manager lowers the assumed utilization to represent demand uncertainty. The tool recalculates the same comparison and makes clear whether a long-term RI still looks economical. The manager can keep uncertain capacity On-Demand or investigate only a conservative baseline for commitment.

The first release is deliberately narrow: Linux C6i in `us-east-1`, public AWS list prices, and one selected instance type at a time. Its outcome is a transparent shortlist for further investigation, never a claim that Riot should purchase a commitment without internal evidence.
