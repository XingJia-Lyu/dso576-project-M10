# Role 6 — Objections

## Audience A: Cloud Infrastructure Lead at Mendix

**Decision:** Decide whether potential EC2 list-price savings from placing additional European application capacity outside `eu-west-1` are large enough to justify a deeper deployment evaluation.

### Possible objections

1. **List price is not the actual cost.**  
   The AWS Price List contains public list prices only. It does not include Mendix's negotiated enterprise discounts, credits, private pricing agreements, taxes, or other customer-specific billing arrangements. Therefore, a lower published price may not produce a lower actual AWS bill.

2. **The current dataset does not cover every target region.**  
   The assigned EC2 data includes `eu-west-1`, but comparing it with regions such as `eu-central-1` or `eu-north-1` requires downloading additional regional price files. A comparison without those files would be incomplete.

3. **EC2 price is only one component of total cost.**  
   The dataset does not include data-transfer charges, EBS storage, support plans, engineering time, migration work, application testing, or possible downtime. These costs may exceed the apparent EC2 savings.

4. **Price data cannot measure operational suitability.**  
   The files do not measure latency, workload performance, capacity availability, reliability, regulatory requirements, GDPR/data residency, or customer experience. Matching vCPU and memory does not guarantee equal real-world performance.

5. **The recommendation may not fit the existing workflow.**  
   Moving capacity to another region could increase operational complexity, monitoring requirements, deployment work, and incident-response burden.

### How the team could address the objections

- Obtain the missing regional EC2 price files before comparing regions.
- Hold operating system, tenancy, instance type, capacity status, and workload assumptions constant.
- Present list-price savings as a screening estimate, not as actual savings.
- Add a total-cost checklist covering networking, storage, migration, compliance, and engineering effort.
- Recommend a small pilot or deeper evaluation before changing deployment regions.

### Unresolved concerns

- What private discounts, credits, and real billing rates does Mendix receive?
- Which European regions meet Mendix's latency, data-residency, and customer-support requirements?
- What is the expected migration and operational cost?

---

## Audience B: FinOps Manager at Riot Games

**Decision:** Decide what portion of a stable C6i/R6i compute baseline should remain On-Demand versus be covered by a 1-year or 3-year Reserved Instance under No Upfront, Partial Upfront, or All Upfront terms.

### Possible objections

1. **A stable baseline must be demonstrated first.**  
   Player demand, game launches, and live events can create large changes in compute demand. A Reserved Instance is appropriate only for capacity that is consistently used.

2. **The data does not prove Riot Games uses C6i/R6i.**  
   The public price list cannot show Riot's actual instance inventory, utilization, workload type, or internal billing data. The selected instance families must be verified with internal data.

3. **List-price breakeven is not actual breakeven.**  
   Riot Games may receive private discounts, credits, or enterprise pricing. A calculation based only on public list prices can overstate or understate actual savings.

4. **Savings Plans are outside the assigned dataset.**  
   Savings Plans are an important real-world alternative, but they are not included in the current price-list files. A Reserved Instance recommendation should disclose this limitation.

5. **Three-year commitments create idle-capacity risk.**  
   If demand falls or infrastructure changes, a long commitment can leave the company paying for unused capacity. The analysis needs utilization scenarios and a cost-of-capital assumption.

6. **Reserved pricing must be calculated carefully.**  
   A Reserved Instance can have an upfront-fee row and an hourly-rate row. The analysis must pair the correct rows and convert each option into an effective hourly cost.

### How the team could address the objections

- Use internal utilization data to estimate a conservative stable baseline.
- Compare several scenarios, such as 60%, 80%, and 95% utilization.
- Calculate effective hourly cost by combining upfront fees and hourly charges.
- Separate Standard and Convertible Reserved Instances.
- Present the output as a recommendation for what portion of capacity to commit, rather than a simple “buy” or “do not buy” result.

### Unresolved concerns

- What are Riot Games' actual instance inventory, utilization, discounts, and credits?
- How much demand is predictable over one year versus three years?
- Would Savings Plans be more flexible or financially attractive than Reserved Instances?
- What is Riot Games' cost of capital and tolerance for unused capacity?

---

## Sources and checks

- Checked `data_overview_aws-price-list.md` for dataset scope and limitations.
- Confirmed that the dataset contains public list prices, On-Demand pricing, and Reserved Instance pricing.
- Confirmed that Savings Plans, private discounts, credits, actual billing data, and performance measurements are not included in the assigned dataset.

## Open questions

- Which additional European region files should be added for the Mendix comparison?
- Has the team confirmed that these are the final two audiences?
- What evidence can be obtained for the stakeholders' actual workload and decision constraints?
