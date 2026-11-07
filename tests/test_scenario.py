from decimal import Decimal as D
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from src.scenario import calculate_scenario, financial_measures, RESULT_COLUMNS

def prices(years=1,p="0.20",h="0.12",f="0",payment="No Upfront"):
    return pd.DataFrame([dict(price_list_version="v1",publication_date="2026-01-01",
        instance_type="c6i.large",term_years=years,purchase_option=payment,
        offering_class="standard",on_demand_hourly_usd=p,ri_hourly_usd=h,
        ri_upfront_usd=f,effective_ri_hourly_usd="999")])

@pytest.mark.parametrize("u,savings,status",[("0.8","350.40","RI lower modeled cost"),
    ("0.6","0","Break-even"),("0.5","-175.20","On-Demand lower modeled cost")])
def test_one_year_fixture(u,savings,status):
    table=prices(); before=table.copy(deep=True)
    r=calculate_scenario(table,"c6i.large",D(u)).iloc[0]
    assert r.ri_annualized_cost_usd == D("1051.20")
    assert r.annual_savings_vs_od_usd == D(savings)
    assert r.break_even_utilization == D(".6")
    assert r.comparison_status == status
    assert r.effective_ri_hourly_usd == D("999")  # display field never drives cost
    assert_frame_equal(table,before)

def test_three_year_fixture():
    r=calculate_scenario(prices(3,h="0",f="1576.80",payment="All Upfront"),"c6i.large",D(".8")).iloc[0]
    assert r.ri_upfront_usd == D("1576.80")
    assert r.ri_annualized_cost_usd == D("525.60")
    assert r.on_demand_annual_cost_usd == D("1401.60")
    assert r.annual_savings_vs_od_usd == D("876")
    assert r.break_even_utilization == D(".3")
    assert financial_measures(D(".2"),D(0),D("1576.80"),3,D(".8"))["effective_ri_hourly_usd"] == D(".06")

@pytest.mark.parametrize("years",[1,3])
@pytest.mark.parametrize("payment,h,f",[("No Upfront","0.1","0"),("Partial Upfront","0.05","438"),("All Upfront","0","876")])
def test_all_payments_terms(years,payment,h,f):
    for u in ["0",".5","1"]:
        r=calculate_scenario(prices(years,h=h,f=f,payment=payment),"c6i.large",D(u)).iloc[0]
        expected=D(f)+D(h)*8760*years
        assert r.ri_annualized_cost_usd == expected/years
        assert r.annual_savings_vs_od_usd == (D(".2")*D(u)*8760*years-expected)/years
        assert r.break_even_utilization == expected/(D(".2")*8760*years)

def test_above_100():
    r=calculate_scenario(prices(h=".25"),"c6i.large",D(1)).iloc[0]
    assert r.break_even_utilization == D("1.25")
    assert r.comparison_status == "On-Demand lower modeled cost"

@pytest.mark.parametrize("u",["NaN","Infinity","-.1","1.1"])
def test_invalid_runtime(u):
    with pytest.raises(ValueError): calculate_scenario(prices(),"c6i.large",D(u))

def test_empty():
    r=calculate_scenario(prices(),"missing",D(".8"))
    assert r.empty and all(c in r for c in RESULT_COLUMNS)

def test_precision():
    m=financial_measures(D(".2"),D("0"),D("1"),3,D(1))
    assert len(str(m["effective_ri_hourly_usd"]).replace(".","").lstrip("0")) == 28

def test_positive_od():
    with pytest.raises(ValueError): calculate_scenario(prices(p="0"),"c6i.large",D(".8"))
