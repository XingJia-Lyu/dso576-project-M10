import csv
import json
from pathlib import Path
import pandas as pd
import pytest
from src.prepare_data import read_source
from src.filter_rates import filter_rates
from src.pair_rates import pair_rates

ROOT=Path(__file__).resolve().parents[1]

def test_full_snapshot_independent_reconciliation():
    raw_path=ROOT/"data/raw/ec2_us-east-1.csv"
    if not raw_path.exists(): pytest.skip("Full raw snapshot is optional for runtime-only checkout")
    raw,meta=read_source(raw_path)
    # Independent explicit selection, without reusing filter constants.
    scope=raw.loc[
        raw["Product Family"].eq("Compute Instance") &
        raw["Region Code"].eq("us-east-1") &
        raw["Operating System"].eq("Linux") &
        raw["Tenancy"].eq("Shared") &
        raw["CapacityStatus"].eq("Used") &
        raw["Pre Installed S/W"].eq("NA") &
        raw["MarketOption"].eq("OnDemand") &
        raw["License Model"].eq("No License required") &
        raw["Instance Type"].str.startswith("c6i.") &
        raw["TermType"].eq("Reserved") &
        raw["OfferingClass"].eq("standard")
    ]
    candidates=set(scope[["SKU","OfferTermCode"]].itertuples(index=False,name=None))
    components,filtering=filter_rates(raw,meta)
    options,validation=pair_rates(components,filtering["anomalies"])
    accepted={(r["sku"],r["offer_term_code"]) for r in validation["accepted_groups"]}
    rejected={(r["sku"],r["offer_term_code"]) for r in validation["rejected_groups"]}
    assert not accepted & rejected and candidates==accepted|rejected
    assert all(r["reason"] for r in validation["rejected_groups"])
    assert len(options)==len(accepted)
    for sku,offer in accepted:
        group=scope[scope.SKU.eq(sku)&scope.OfferTermCode.eq(offer)]
        assert len(group[group.Unit.eq("Hrs")])==1
        payment=group.PurchaseOption.iloc[0]
        quantities=group[group.Unit.eq("Quantity")]
        assert (len(quantities)==0 if payment=="No Upfront" else len(quantities)==1)
        od=raw[raw.SKU.eq(sku)&raw.TermType.eq("OnDemand")&raw.Unit.eq("Hrs")]
        assert len(od)==1
    committed=pd.read_parquet(ROOT/"data/processed/c6i_price_options.parquet")
    pd.testing.assert_frame_equal(options,committed)
