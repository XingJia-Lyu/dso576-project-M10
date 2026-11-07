"""Pure component pairing with explicit rejection accounting."""
from collections import Counter
from decimal import Decimal
import pandas as pd
from src.scenario import financial_measures

PRICE_COLUMNS = [
    "price_list_version", "publication_date", "instance_type", "term_years",
    "purchase_option", "offering_class", "on_demand_hourly_usd",
    "ri_upfront_usd", "ri_hourly_usd", "effective_ri_hourly_usd",
]

def pair_rates(components: pd.DataFrame, invalid_components: list):
    reserved = components[components.term_type.eq("Reserved")]
    groups = {(s,o): g for (s,o),g in reserved.groupby(["sku", "offer_term_code"])}
    candidates = set(groups) | {(r["sku"],r["offer_term_code"]) for r in invalid_components if r["term_type"] == "Reserved"}
    bad_groups = {(r["sku"],r["offer_term_code"]) for r in invalid_components if r["term_type"] == "Reserved"}
    bad_od = {r["sku"] for r in invalid_components if r["term_type"] == "OnDemand"}
    rejected, accepted = [], []
    for sku, offer in sorted(candidates):
        reasons = []
        key = dict(sku=sku, offer_term_code=offer)
        if (sku, offer) in bad_groups: reasons.append("Anomalous RI component")
        if sku in bad_od: reasons.append("Anomalous On-Demand component on SKU")
        g = groups.get((sku,offer))
        if g is None:
            rejected.append(key | {"reason": "; ".join(reasons)})
            continue
        attrs = ["instance_type","term_years","purchase_option","offering_class","price_list_version","publication_date"]
        if any(g[a].nunique(dropna=False) != 1 for a in attrs):
            reasons.append("Inconsistent group attributes")
        first = g.iloc[0]
        hrs, qty = g[g.unit.eq("Hrs")], g[g.unit.eq("Quantity")]
        if len(hrs) != 1: reasons.append("Require exactly one Hrs component")
        if first.purchase_option == "No Upfront":
            if len(qty) > 1 or any(Decimal(v) != 0 for v in qty.price_per_unit_usd):
                reasons.append("No Upfront requires absent or one zero Quantity")
        elif len(qty) != 1:
            reasons.append("Require exactly one upfront Quantity")
        od = components[components.term_type.eq("OnDemand") & components.sku.eq(sku) & components.unit.eq("Hrs")]
        if len(od) != 1:
            reasons.append("Require exactly one matching On-Demand Hrs component")
        elif od.iloc[0].instance_type != first.instance_type:
            reasons.append("On-Demand configuration mismatch")
        elif Decimal(od.iloc[0].price_per_unit_usd) <= 0:
            reasons.append("On-Demand price must be positive")
        if reasons:
            rejected.append(key | {"reason": "; ".join(reasons)})
            continue
        p, h = od.iloc[0].price_per_unit_usd, hrs.iloc[0].price_per_unit_usd
        f = qty.iloc[0].price_per_unit_usd if len(qty) else "0"
        row = {a: first[a] for a in attrs}
        row["term_years"] = int(row["term_years"])
        row.update(on_demand_hourly_usd=p,ri_hourly_usd=h,ri_upfront_usd=f,
                   effective_ri_hourly_usd=str(financial_measures(Decimal(p),Decimal(h),Decimal(f),row["term_years"],Decimal(1))["effective_ri_hourly_usd"]))
        accepted.append((key,row))
    counts = Counter((r["instance_type"],r["term_years"],r["purchase_option"]) for _,r in accepted)
    valid = []
    provenance = []
    for key,row in accepted:
        if counts[(row["instance_type"],row["term_years"],row["purchase_option"])] > 1:
            rejected.append(key | {"reason": "Ambiguous instance/term/payment combination"})
        else:
            valid.append(row)
            provenance.append(key | {k:row[k] for k in ["instance_type","term_years","purchase_option"]})
    table = pd.DataFrame(valid, columns=PRICE_COLUMNS)
    return table, dict(candidate_ri_group_count=len(candidates), accepted_group_count=len(valid),
                       rejected_group_count=len(rejected), rejected_groups=rejected,
                       accepted_groups=provenance,
                       valid_option_counts=[dict(instance_type=k[0],term_years=int(k[1]),purchase_option=k[2],count=int(v))
                         for k,v in table.groupby(["instance_type","term_years","purchase_option"]).size().items()])
