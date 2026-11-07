from decimal import Decimal as D
import os
from pathlib import Path
import pandas as pd
from pandas.testing import assert_frame_equal
from streamlit.testing.v1 import AppTest
from tests.test_scenario import prices
from src.scenario import calculate_scenario
from src.views import percent,hourly

ROOT=Path(__file__).resolve().parents[1]

def view_app(table,utilization=D(".8")):
    def app(table,utilization):
        from src.views import render_comparison
        render_comparison(table,"c6i.large",utilization)
    return AppTest.from_function(app,args=(table,utilization)).run()

def test_view_contract_and_empty_states():
    r=calculate_scenario(prices(),"c6i.large",D(".8"))
    before=r.copy(deep=True)
    a=view_app(r)
    assert not a.exception and len(a.dataframe)==1
    assert any("No valid options" in i.value for i in a.info)
    assert_frame_equal(r,before)
    a=view_app(r.drop(columns="ri_hourly_usd"))
    assert "handoff error" in a.error[0].value and not a.dataframe
    a=view_app(r.assign(publication_date=None))
    assert a.error and not a.dataframe
    a=view_app(r.assign(instance_type="c6i.xlarge"))
    assert a.error
    a=view_app(pd.concat([r,r.assign(price_list_version="other")]))
    assert a.error
    a=view_app(r.iloc[:0])
    assert "No valid Reserved Instance" in a.info[0].value

def test_view_full_upfront_and_unattainable():
    r=calculate_scenario(prices(3,h="0",f="1576.80",payment="All Upfront"),"c6i.large",D(".8"))
    a=view_app(r)
    shown=a.dataframe[0].value
    assert shown.iloc[0]["Upfront payment (USD)"]=="$1,576.80"
    assert shown.iloc[0]["Annualized RI cost (USD)"]=="$525.60"
    a=view_app(calculate_scenario(prices(h=".25"),"c6i.large",D(".8")))
    assert a.dataframe[0].value.iloc[0]["Break-even runtime"]=="125.00%"
    assert "unattainable" in a.warning[0].value

def test_formatting_near_break_even():
    assert hourly(D(".000000001")) != "$0.0000"
    assert hourly(D(0))=="$0"
    v=percent(D(".600000001"),D(".6"))
    assert D(v[:-1])>60

def test_controls_runtime_and_cache(tmp_path,monkeypatch):
    import src.load_data as loader
    import streamlit as st
    st.cache_data.clear()
    path=tmp_path/"prices.parquet"
    prices().assign(effective_ri_hourly_usd=".12").to_parquet(path,index=False)
    monkeypatch.setenv("RI_PRICES_PATH",str(path))
    real=loader.load_price_options
    calls=[]
    def counted(p):
        calls.append(p)
        return real(p)
    monkeypatch.setattr(loader,"load_price_options",counted)
    def no_raw(*args,**kwargs):
        raise AssertionError("Runtime must not read CSV")
    monkeypatch.setattr(pd,"read_csv",no_raw)
    a=AppTest.from_file(str(ROOT/"dashboard.py")).run()
    assert not a.exception and not a.dataframe
    assert a.selectbox[0].value is None and a.number_input[0].value==80
    a.selectbox[0].select("c6i.large").run()
    assert not a.exception and len(a.dataframe)==2
    assert a.dataframe[0].value.iloc[0]["Annual savings vs OD (USD)"]=="$350.40"
    a.number_input[0].set_value(60).run()
    assert a.dataframe[0].value.iloc[0]["Comparison status"]=="Break-even"
    a.number_input[0].set_value(50).run()
    assert a.dataframe[0].value.iloc[0]["Annual savings vs OD (USD)"]=="$-175.20"
    assert len(calls)==1
    prices(h=".15").to_parquet(path,index=False)
    stamp=path.stat().st_mtime_ns+1_000_000
    os.utime(path,ns=(stamp,stamp))
    a.run()
    assert not a.exception and len(calls)==2
    assert a.dataframe[0].value.iloc[0]["Recurring RI / h"]=="$0.1500"
    path.unlink()
    a.run()
    assert a.error and "prepare_data" in a.error[0].value

def test_real_snapshot_vision_walkthrough():
    from src.load_data import load_price_options
    p=load_price_options(ROOT/"data/processed/c6i_price_options.parquet")
    a=AppTest.from_file(str(ROOT/"dashboard.py")).run()
    assert not a.exception
    a.selectbox[0].select("c6i.large").run()
    assert len(a.dataframe)==3 and all(len(x.value)==3 for x in a.dataframe[:2])
    assert any(p.publication_date.iloc[0] in c.value for c in a.caption)
    assert any(p.price_list_version.iloc[0] in c.value for c in a.caption)
    a.number_input[0].set_value(10).run()
    assert all((x.value["Comparison status"]=="On-Demand lower modeled cost").all() for x in a.dataframe[:2])
    assert all(x.value["Annual savings vs OD (USD)"].str.startswith("$-").all() for x in a.dataframe[:2])
