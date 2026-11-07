from decimal import Decimal as D
import pandas as pd
import pytest
from src.decision import eligible_options, sensitivity_table
from src.scenario import calculate_scenario
from tests.test_scenario import prices


def fixture():
    p = pd.concat([prices(), prices(h='0', f='876', payment='All Upfront'),
                   prices(years=3, h='0', f='1576.80', payment='All Upfront')], ignore_index=True)
    return calculate_scenario(p, 'c6i.large', D('.8'))


def test_budget_boundary_and_term():
    r = fixture()
    e = eligible_options(r, 1, D('876'))
    assert len(e) == 2
    assert set(e.term_years) == {1}
    assert len(eligible_options(r, 1, D('875.99'))) == 1
    assert len(eligible_options(r, 3, D('1576.80'))) == 3
    assert len(r) == 3


def test_no_eligible_ri():
    r = fixture().query("purchase_option == 'All Upfront'")
    assert eligible_options(r, 1, D('0')).empty


@pytest.mark.parametrize('budget', ['-1', 'NaN', 'Infinity'])
def test_invalid_budget(budget):
    with pytest.raises(ValueError): eligible_options(fixture(), 1, D(budget))


def test_sensitivity_independent_reference_and_current_scenario():
    r = fixture()
    table = sensitivity_table(r)
    assert len(table) == 303
    no = table.loc[table.option.eq('1y · No Upfront')].set_index('runtime_percent')
    # Independently calculated: 0.12 * 24 * 365 = 1051.20;
    # OD at 80%: 0.20 * 24 * 365 * 0.8 = 1401.60.
    assert no.loc[0, 'od_cost'] == 0
    assert no.loc[100, 'od_cost'] == D('1752')
    assert no.loc[80, 'od_cost'] == D('1401.60')
    assert no.ri_cost.eq(D('1051.20')).all()
    assert no.loc[60, 'od_cost'] == no.loc[60, 'ri_cost']
    for row in r.itertuples():
        point = table.loc[table.option.eq(f'{row.term_years}y · {row.purchase_option}') & table.runtime_percent.eq(80)].iloc[0]
        assert point.ri_cost == row.ri_annualized_cost_usd
        assert point.od_cost == row.on_demand_annual_cost_usd


def test_ui_constraints_and_chart():
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'dashboard.py')).run()
    app.selectbox(key='instance_type').select('c6i.large').run()
    assert not app.exception
    assert len(app.get('vega_lite_chart')) == 1
    app.selectbox(key='max_years').select(1).run()
    app.number_input(key='max_upfront').set_value(0.0).run()
    assert not app.exception
    shortlist = app.dataframe[2].value
    assert shortlist['Term (years)'].eq(1).all()
    assert shortlist['Upfront (USD)'].eq('$0.00').all()
    app.number_input(key='runtime_percent').set_value(0).run()
    assert not app.exception
    assert any('more per modeled year' in w.value for w in app.warning)
