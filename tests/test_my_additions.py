from decimal import Decimal as D

import pandas as pd
from pandas.testing import assert_frame_equal

from src.scenario import calculate_scenario
from tests.test_scenario import prices


def test_selected_instance_isolated_from_other_instances():
    large_no = prices()
    large_all = prices(
        h="0", f="876", payment="All Upfront"
    )
    other = prices(p="0.40", h="0.30").assign(
        instance_type="c6i.xlarge"
    )
    mixed = pd.concat(
        [other, large_all, large_no], ignore_index=True
    )
    before = mixed.copy(deep=True)

    result = calculate_scenario(mixed, "c6i.large", D("0.8"))

    assert len(result) == 2
    assert set(result["instance_type"]) == {"c6i.large"}
    assert set(result["purchase_option"]) == {
        "No Upfront", "All Upfront"
    }
    assert result["on_demand_hourly_usd"].eq(D("0.20")).all()

    by_payment = result.set_index("purchase_option")
    assert by_payment.loc[
        "No Upfront", "ri_annualized_cost_usd"
    ] == D("1051.20")
    assert by_payment.loc[
        "All Upfront", "ri_annualized_cost_usd"
    ] == D("876")
    assert_frame_equal(mixed, before)


def test_real_snapshot_runtime_relationships():
    from pathlib import Path
    from src.load_data import load_price_options

    root = Path(__file__).resolve().parents[1]
    table = load_price_options(
        root / "data/processed/c6i_price_options.parquet"
    )
    keys = ["term_years", "purchase_option"]

    for instance in sorted(table["instance_type"].unique()):
        expected_keys = pd.MultiIndex.from_frame(
            table.loc[table["instance_type"].eq(instance), keys]
        ).sort_values()

        low = calculate_scenario(
            table, instance, D("0.25")
        ).set_index(keys).sort_index()
        high = calculate_scenario(
            table, instance, D("0.75")
        ).set_index(keys).sort_index()

        assert low.index.equals(expected_keys)
        assert high.index.equals(expected_keys)

        for key in expected_keys:
            a = low.loc[key]
            b = high.loc[key]

            assert (
                a["ri_annualized_cost_usd"]
                == b["ri_annualized_cost_usd"]
            )
            assert (
                a["break_even_utilization"]
                == b["break_even_utilization"]
            )
            assert (
                b["on_demand_annual_cost_usd"]
                == a["on_demand_annual_cost_usd"] * D("3")
            )

            od_increase = (
                b["on_demand_annual_cost_usd"]
                - a["on_demand_annual_cost_usd"]
            )
            savings_increase = (
                b["annual_savings_vs_od_usd"]
                - a["annual_savings_vs_od_usd"]
            )

            assert od_increase > 0
            assert savings_increase == od_increase
