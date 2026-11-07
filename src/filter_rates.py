"""Pure fixed-scope filtering; anomalies remain visible to pairing."""
from collections import Counter
from decimal import Decimal, InvalidOperation
import pandas as pd

SCOPE = {
    "Product Family": "Compute Instance", "Region Code": "us-east-1",
    "Operating System": "Linux", "Tenancy": "Shared", "CapacityStatus": "Used",
    "Pre Installed S/W": "NA", "MarketOption": "OnDemand",
    "License Model": "No License required",
}
REQUIRED_COLUMNS = list(SCOPE) + [
    "Instance Type", "SKU", "OfferTermCode", "TermType", "OfferingClass",
    "LeaseContractLength", "PurchaseOption", "Unit", "Currency",
    "PricePerUnit", "StartingRange", "EndingRange",
]
PAYMENTS = ["No Upfront", "Partial Upfront", "All Upfront"]
LEASES = {"1yr": 1, "1 yr": 1, "3yr": 3, "3 yr": 3}
PAYMENT_MAP = {p: p for p in PAYMENTS} | {p.replace(" ", ""): p for p in PAYMENTS}
COMPONENT_COLUMNS = [
    "price_list_version", "publication_date", "sku", "offer_term_code",
    "instance_type", "term_type", "term_years", "purchase_option",
    "offering_class", "unit", "price_per_unit_usd",
]

def filter_rates(raw: pd.DataFrame, metadata: dict):
    missing = set(REQUIRED_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing raw columns: {sorted(missing)}")
    rows = raw[REQUIRED_COLUMNS].apply(lambda s: s.str.strip())
    active = pd.Series(True, index=rows.index)
    exclusions = Counter()
    for field, value in SCOPE.items():
        bad = active & rows[field].ne(value)
        exclusions[field] = int(bad.sum())
        active &= ~bad
    for reason, eligible in [
        ("Instance Type", rows["Instance Type"].str.startswith("c6i.")),
        ("TermType", rows["TermType"].isin(["OnDemand", "Reserved"])),
        ("OfferingClass", rows["TermType"].ne("Reserved") | rows["OfferingClass"].eq("standard")),
    ]:
        bad = active & ~eligible
        exclusions[reason] = int(bad.sum())
        active &= ~bad
    kept, anomalies, candidates = [], [], set()
    for r in rows[active].to_dict("records"):
        ri = r["TermType"] == "Reserved"
        key = {"sku": r["SKU"], "offer_term_code": r["OfferTermCode"], "term_type": r["TermType"]}
        if ri:
            candidates.add((r["SKU"], r["OfferTermCode"]))
        reasons = []
        term = LEASES.get(r["LeaseContractLength"]) if ri else None
        payment = PAYMENT_MAP.get(r["PurchaseOption"]) if ri else "OnDemand"
        if ri and term is None: reasons.append("Unrecognized lease label")
        if ri and payment is None: reasons.append("Unrecognized payment label")
        if r["Unit"] not in (["Hrs", "Quantity"] if ri else ["Hrs"]):
            reasons.append("Unsupported unit")
        if r["Currency"] != "USD": reasons.append("Currency is not USD")
        try:
            price = Decimal(r["PricePerUnit"])
            if not price.is_finite() or price < 0: raise ValueError()
        except (InvalidOperation, ValueError):
            reasons.append("Invalid nonnegative finite price")
        if r["Unit"] == "Hrs" and (r["StartingRange"] != "0" or r["EndingRange"] != "Inf"):
            reasons.append("Unsupported hourly range")
        if r["Unit"] == "Quantity" and (r["StartingRange"] or r["EndingRange"]):
            reasons.append("Unsupported quantity range")
        if reasons:
            anomalies.append(key | {"reason": "; ".join(reasons)})
            continue
        kept.append(dict(
            price_list_version=metadata["price_list_version"],
            publication_date=metadata["publication_date"], **key,
            instance_type=r["Instance Type"], term_years=term,
            purchase_option=payment, offering_class="standard" if ri else None,
            unit=r["Unit"], price_per_unit_usd=r["PricePerUnit"],
        ))
    components = pd.DataFrame(kept, columns=COMPONENT_COLUMNS)
    components["term_years"] = components["term_years"].astype("Int64")
    report = dict(metadata, input_row_count=len(raw), retained_component_count=len(components),
                  retained_by_term=components["term_type"].value_counts().to_dict(),
                  retained_instance_types=sorted(components["instance_type"].unique()),
                  scope_exclusions=dict(exclusions), scope_exclusion_policy="First failing condition",
                  anomalies=anomalies,
                  candidate_ri_groups=[dict(sku=s, offer_term_code=o) for s,o in sorted(candidates)])
    return components, report
