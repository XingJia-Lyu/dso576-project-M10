# Role 6 — Objections

## Audience A: Cloud Infrastructure Lead at Mendix

**Decision:** Decide whether lower EC2 prices in other European regions are worth further evaluation.

### Main concerns

- AWS list prices may be different from Mendix's real prices because of discounts or credits.
- The current data only includes `eu-west-1`, so more regional files are needed.
- EC2 price does not include network, storage, migration, or support costs.
- Price data does not show latency, performance, compliance, or customer impact.
- Moving to another region may create more operational work.

### How to address these concerns

- Download the missing regional price files.
- Use the price comparison only as a first estimate.
- Consider migration cost, performance, and compliance before making a final decision.

### Open questions

- What discounts or credits does Mendix receive?
- Which regions meet Mendix's performance and data-residency needs?

---

## Audience B: FinOps Manager at Riot Games

**Decision:** Decide whether stable C6i/R6i capacity should stay On-Demand or use 1-year or 3-year Reserved Instances.

### Main concerns

- Game demand may change, so the stable baseline must be checked first.
- Public data does not show Riot Games' real usage or actual instance types.
- List prices may be different from Riot's real prices because of discounts or credits.
- Savings Plans are not included in the current dataset.
- A 3-year commitment may create unused-capacity risk.
- Reserved Instance prices need careful calculation because upfront and hourly fees are on separate rows.

### How to address these concerns

- Use different usage scenarios, such as low, medium, and high utilization.
- Calculate the full cost of each Reserved Instance option.
- Recommend committing only part of the capacity, not all of it.

### Open questions

- How stable is Riot Games' compute demand?
- Would Savings Plans be better than Reserved Instances?
- What discounts or credits does Riot Games receive?

---

## Sources and checks

- Used `data_overview_aws-price-list.md`.
- The dataset has public list prices, On-Demand prices, and Reserved Instance prices.
- It does not include private discounts, actual billing data, Savings Plans, or performance data.
