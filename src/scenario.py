"""The single definition of modeled financial measures."""
from decimal import Decimal, localcontext
import pandas as pd

MONEY = ["on_demand_hourly_usd", "ri_upfront_usd", "ri_hourly_usd", "effective_ri_hourly_usd"]
RESULT_COLUMNS = [
    "ri_annualized_cost_usd", "on_demand_annual_cost_usd",
    "annual_savings_vs_od_usd", "break_even_utilization", "comparison_status",
]

def financial_measures(p: Decimal, h: Decimal, upfront: Decimal, years: int, u: Decimal):
    if not u.is_finite() or not 0 <= u <= 1:
        raise ValueError("Expected billable runtime must be finite and between 0 and 1.")
    if not p.is_finite() or p <= 0:
        raise ValueError("On-Demand hourly price must be positive and finite.")
    if years not in (1, 3) or any(not v.is_finite() or v < 0 for v in (h, upfront)):
        raise ValueError("Invalid RI term or charge.")
    with localcontext() as ctx:
        ctx.prec = 28
        t = Decimal(8760) * years
        ri = upfront + h * t
        od = p * u * t
        savings = od - ri
        return dict(
            effective_ri_hourly_usd=ri / t,
            ri_annualized_cost_usd=ri / years,
            on_demand_annual_cost_usd=od / years,
            annual_savings_vs_od_usd=savings / years,
            break_even_utilization=ri / (p * t),
            comparison_status=("RI lower modeled cost" if savings > 0 else
                               "On-Demand lower modeled cost" if savings < 0 else "Break-even"),
        )

def calculate_scenario(price_options: pd.DataFrame, instance_type: str, utilization: Decimal) -> pd.DataFrame:
    if not utilization.is_finite() or not 0 <= utilization <= 1:
        raise ValueError("Expected billable runtime must be finite and between 0 and 1.")
    selected = price_options.loc[price_options.instance_type.eq(instance_type)].copy()
    output = []
    for row in selected.to_dict("records"):
        for field in MONEY:
            row[field] = Decimal(row[field])
        measures = financial_measures(row["on_demand_hourly_usd"], row["ri_hourly_usd"],
                                      row["ri_upfront_usd"], int(row["term_years"]), utilization)
        measures.pop("effective_ri_hourly_usd")  # Stored value is display-only.
        output.append(row | measures)
    return pd.DataFrame(output, columns=list(price_options.columns) + RESULT_COLUMNS)
