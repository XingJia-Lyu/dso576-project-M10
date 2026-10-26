**Cloud Infrastructure Lead**
# 1. Scenario
I am a Cloud Infrastructure Lead at Mendix. Today I need to decide whether differences in AWS EC2 list prices across European regions are large enough to justify further evaluation of where to deploy additional application capacity.

# 2. Decision process
## People involved
Finance lead: helps evaluate the cost and financial impact.

Site Reliability Engineer lead: Provide input on application usage, reliability, and capacity needs when necessary.
## Required information
AWS EC2 list prices in different European regions.

Current and expected application capacity needs.

Current EC2 instance types and how much capacity they provide.

Expected usage of the applications.
## Steps
(1) Check current capacity needs: Review current application usage and discuss future capacity needs with the SRE Lead.

(2) Compare AWS prices: Look up EC2 list prices for the relevant instance types in different European regions.

(3) Estimate the cost difference: Use the prices and expected capacity to estimate how much the company would pay in each region.

(4) Check other factors: Consider whether a cheaper region could create problems with performance, latency, data location, or operations.

(5) Decide whether further evaluation is needed: If the price difference is large enough to matter, recommend a deeper evaluation of where to deploy additional application capacity. If the difference is small, keep the current approach and avoid unnecessary analysis.

(6) Present the decision: Report the final decision to the relevant stakeholders.

# 3. Three Google searches
(1) AWS EC2 historical usage capacity planning

(2) AWS compare EC2 costs across regions

(3) AWS region selection impact

# 4. Evidence
(1) EC2 Capacity Manager offers customers a comprehensive view of On-Demand, Spot, and Capacity Reservation usage across their accounts and Regions. It provides historical usage trends to help customers gain a better understanding of their capacity patterns over time. 
source: https://aws.amazon.com/cn/about-aws/whats-new/2025/10/amazon-ec2-capacity-manager/

(2) The AWS Pricing Calculator allows customers to filter and view prices by region.
source: https://aws.amazon.com/blogs/aws/check-it-out-new-aws-pricing-calculator-for-ec2-and-ebs/

(3) Choosing an AWS region involves more than cost. Data residency, compliance, latency, performance, and pricing can all vary between regions.
source: https://aws.amazon.com/blogs/architecture/what-to-consider-when-selecting-a-region-for-your-workloads/?utm_source=chatgpt.com


**FinOps Manager**
# 1. Scenario
I am a FinOps Manager at Riot Games. Today I need to decide whether a stable baseline of C6i & R6i compute capacity should remain On-Demand or use a 1-year or 3-year Reserved Instance with No Upfront, Partial Upfront, or All Upfront payment.

# 2. Decision process
## People involved
Lead infrastructure engineer: Tells me the exact size and number of C6i and R6i instances needed to run the 24/7 game servers continuously.

Finance lead: Informs me of available cash reserves to decide if we can afford a large, one-time cash payment for an All Upfront plan.

AWS account executive: Clarifies our current Enterprise Discount Program terms and whether custom credits apply.
## Required information
AWS Pricing Calculator: Search unit rates for C6i and R6i across different payment options and target regions.

Historical CloudWatch metrics: Retrieve past 3 to 6 months of compute usage data to confirm the stable baseline.

Company cash flow statements: Use financial reports to assess quarterly capital availability.
## Steps
(1) Confirm the compute baseline: I meet with the lead infrastructure engineer to look at usage history and lock in the exact size for C6i and R6i instances that run 24/7 without scaling down.

(2) Collect prices manually: Without a bulk API tool, I manually look up hourly rates and upfront fees for C6i and R6i across 7 purchasing combinations (On-Demand, 1-year No/Partial/All Upfront, 3-year No/Partial/All Upfront) using the AWS Pricing Calculator.

(3) Build an Excel model: I copy these prices into a spreadsheet to calculate the total cost over 1 and 3 years, comparing the overall savings of each Reserved Instance option against On-Demand.

(4) Assess financial risks: I check with finance lead to see if locking in a 3-year All Upfront contract creates a cash flow risk or leaves us with unused capacity if game traffic drops.

(5) Present and make final decision: I bring the cost comparison table to the engineering and finance leads to agree on the best balance between maximum discount and cash flexibility.

# 3. Three Google searches
(1) How do companies use historical EC2 usage to determine baseline capacity for Reserved Instances?

(2) How to compare the cost of AWS EC2 On-Demand vs Reserved Instances 1 year / 3 year upfront？

(3) Financial risk of unused capacity commitments in AWS RIs.

# 4. Evidence
(1) AWS provides EC2 Instance Usage Reports that show historical EC2 usage and cost data, with hourly, daily, and monthly views. The reports can also be filtered by instance type, region, and purchase option.
source: https://aws.amazon.com/cn/blogs/aws/amazon-ec2-instance-usage-and-reserved-instance-utilization-reports/

(2) We can not get any evidence that Riot Games use Excel table to input different prices and make analysis.

(3)  Once you purchase an RI, you are financially obligated to pay for the entire term. If workloads are downsized or migrated off AWS, the unused capacity goes straight to waste while billing continues unabated. So, we need to consider financial risks when making decisions.
source: https://www.usage.ai/blogs/aws/savings-plans/ec2/savings-plans-vs-reserved-instances/