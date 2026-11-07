import json
from pathlib import Path
import pandas as pd
import pytest
from src.filter_rates import SCOPE, filter_rates
from src.pair_rates import pair_rates
from src.load_data import load_price_options, ProcessedDataError
from tests.test_scenario import prices

META=dict(price_list_version="v1",publication_date="2026-01-01")

def raw_row(term="Reserved",unit="Hrs",**changes):
    row=dict(SCOPE,**{"Instance Type":"c6i.large","SKU":"sku","OfferTermCode":"ri" if term=="Reserved" else "od",
        "TermType":term,"OfferingClass":"standard","LeaseContractLength":"1yr",
        "PurchaseOption":"No Upfront","Unit":unit,"Currency":"USD","PricePerUnit":".12" if term=="Reserved" else ".2",
        "StartingRange":"0" if unit=="Hrs" else "","EndingRange":"Inf" if unit=="Hrs" else ""})
    return row | changes

def run(rows):
    c,f=filter_rates(pd.DataFrame(rows),META)
    p,v=pair_rates(c,f["anomalies"])
    assert v["candidate_ri_group_count"]==v["accepted_group_count"]+v["rejected_group_count"]
    assert all(x["reason"] for x in v["rejected_groups"])
    return c,f,p,v

def test_zero_hourly_all_upfront_blank_quantity():
    _,f,p,v=run([raw_row("OnDemand"),raw_row(PricePerUnit="0",PurchaseOption="All Upfront"),
                 raw_row(unit="Quantity",PurchaseOption="All Upfront",PricePerUnit="876")])
    assert len(p)==1 and not f["anomalies"] and p.iloc[0].ri_hourly_usd=="0"

@pytest.mark.parametrize("rows",[
    [raw_row(unit="Quantity",PricePerUnit="0")],
    [raw_row(),raw_row()],
    [raw_row(),raw_row(unit="Quantity",PricePerUnit="0"),raw_row(unit="Quantity",PricePerUnit="0")],
    [raw_row(PurchaseOption="Partial Upfront")],
    [raw_row(),raw_row(unit="Quantity",PricePerUnit="1")],
    [raw_row(),raw_row(unit="Quantity",PricePerUnit="0",StartingRange="0")],
    [raw_row(StartingRange="1")],
    [raw_row(LeaseContractLength="2yr")],
    [raw_row(PurchaseOption="Unknown")],
    [raw_row(Unit="Seconds")],
    [raw_row(Currency="EUR")],
    [raw_row(PricePerUnit="NaN")],
    [raw_row(PricePerUnit="-1")],
])
def test_bad_components_and_groups(rows):
    _,_,p,v=run([raw_row("OnDemand")]+rows)
    assert p.empty and v["rejected_groups"]

@pytest.mark.parametrize("od", [[],[raw_row("OnDemand"),raw_row("OnDemand")],
    [raw_row("OnDemand",PricePerUnit="garbage")],
    [raw_row("OnDemand",**{"Instance Type":"c6i.xlarge"})]])
def test_invalid_od(od):
    _,_,p,v=run(od+[raw_row()])
    assert p.empty and len(v["rejected_groups"])==1

def test_scope_exclusions_do_not_stop():
    _,f,p,_=run([raw_row("OnDemand"),raw_row(),raw_row(MarketOption="Spot")])
    assert len(p)==1 and f["scope_exclusions"]["MarketOption"]==1 and not f["anomalies"]

def test_ambiguous_groups():
    _,_,p,v=run([raw_row("OnDemand"),raw_row(),raw_row(OfferTermCode="other")])
    assert p.empty and v["rejected_group_count"]==2
    assert all("Ambiguous" in r["reason"] for r in v["rejected_groups"])

def test_variants_and_whitespace_od_lease_ignored():
    _,_,p,_=run([raw_row("OnDemand",LeaseContractLength="bad",PurchaseOption="bad"),
        raw_row(LeaseContractLength=" 1 yr ",PurchaseOption="NoUpfront")])
    assert len(p)==1 and p.iloc[0].purchase_option=="No Upfront"

def test_group_consistency():
    _,_,p,v=run([raw_row("OnDemand"),raw_row(PurchaseOption="Partial Upfront"),
        raw_row(unit="Quantity",PurchaseOption="All Upfront",PricePerUnit="1")])
    assert p.empty and "Inconsistent" in v["rejected_groups"][0]["reason"]

@pytest.mark.parametrize("mutator",[
    lambda p:p.drop(columns="ri_hourly_usd"),
    lambda p:pd.concat([p,p.assign(price_list_version="other")]),
    lambda p:p.assign(ri_upfront_usd="NaN"),
    lambda p:p.assign(on_demand_hourly_usd="0"),
    lambda p:pd.concat([p,p]),
    lambda p:p.assign(term_years=2),
    lambda p:p.assign(ri_hourly_usd=None),
    lambda p:p.assign(purchase_option="bad"),
])
def test_loader_rejections(tmp_path,mutator):
    p=tmp_path/"prices.parquet"
    mutator(prices()).to_parquet(p,index=False)
    with pytest.raises(ProcessedDataError,match="uv run python -m src.prepare_data"):
        load_price_options(p)

def test_loader_success(tmp_path):
    p=tmp_path/"prices.parquet"; prices().to_parquet(p,index=False)
    loaded=load_price_options(p)
    assert isinstance(loaded.iloc[0].ri_hourly_usd,str)

def test_loader_missing(tmp_path):
    with pytest.raises(ProcessedDataError): load_price_options(tmp_path/"no.parquet")

def test_failed_preparation_preserves_published_files(tmp_path,monkeypatch):
    import src.prepare_data as prep
    root=tmp_path/"app"; output=root/"data/processed"; output.mkdir(parents=True)
    (output/"c6i_price_options.parquet").write_bytes(b"previous")
    source=tmp_path/"broken.csv"; source.write_text("bad")
    monkeypatch.setattr(prep,"ROOT",root)
    with pytest.raises(ValueError): prep.prepare(source)
    assert (output/"c6i_price_options.parquet").read_bytes()==b"previous"
    assert json.loads((output/"failed_report.json").read_text())["reason"]

def test_source_lookup_refresh_override(tmp_path,monkeypatch):
    import src.prepare_data as prep
    root=tmp_path/"app"; root.mkdir()
    dataset=tmp_path/"dataset_aws-price-list/data"; dataset.mkdir(parents=True)
    source=dataset/"ec2_us-east-1.csv"; source.write_text("dataset")
    monkeypatch.setattr(prep,"ROOT",root)
    assert prep.resolve_source()==source
    override=tmp_path/"override.csv"; override.write_text("override")
    assert prep.resolve_source(override)==override
    monkeypatch.setattr(prep.urllib.request,"urlretrieve",lambda url,p:Path(p).write_text("new"))
    assert prep.resolve_source(refresh=True).read_text()=="new"
    assert source.read_text()=="dataset" and override.read_text()=="override"
    with pytest.raises(ValueError): prep.resolve_source(override,True)

@pytest.mark.parametrize("ri_rows",[
    [raw_row(unit="Quantity",PricePerUnit="0")],
    [raw_row(MarketOption="Spot")],
])
def test_stage_failures_preserve_all_published_outputs(tmp_path,monkeypatch,ri_rows):
    import csv
    import src.prepare_data as prep
    from src.filter_rates import REQUIRED_COLUMNS
    root=tmp_path/"app"; output=root/"data/processed"; output.mkdir(parents=True)
    names=["c6i_price_options.parquet","c6i_filtered_rate_components.parquet","filtering_report.json","validation_report.json"]
    for name in names: (output/name).write_bytes(b"previous")
    source=tmp_path/"source.csv"
    with source.open("w",newline="") as f:
        writer=csv.writer(f)
        writer.writerows([["FormatVersion","v1"],["Disclaimer","test"],["Publication Date","2026-01-01"],["Version","v1"],["OfferCode","AmazonEC2"]])
        writer=csv.DictWriter(f,fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows([raw_row("OnDemand")]+ri_rows)
    monkeypatch.setattr(prep,"ROOT",root)
    with pytest.raises(ValueError,match="Data availability"): prep.prepare(source)
    assert all((output/name).read_bytes()==b"previous" for name in names)
    assert (output/"failed_report.json").exists()
