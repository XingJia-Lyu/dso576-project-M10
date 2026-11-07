"""Planning constraints and runtime sensitivity, using the existing cost model."""
from decimal import Decimal
import pandas as pd
from src.scenario import financial_measures


def eligible_options(results, max_years, max_upfront):
    if max_years not in (1, 3):
        raise ValueError('Maximum term must be 1 or 3 years.')
    budget = Decimal(str(max_upfront))
    if not budget.is_finite() or budget < 0:
        raise ValueError('Upfront budget must be finite and nonnegative.')
    return results.loc[
        results.term_years.le(max_years) & results.ri_upfront_usd.le(budget)
    ].copy()


def sensitivity_table(results):
    """Exact Decimal costs for every integer runtime percentage and option."""
    records = []
    for row in results.itertuples():
        label = f'{row.term_years}y · {row.purchase_option}'
        for runtime in range(101):
            m = financial_measures(row.on_demand_hourly_usd, row.ri_hourly_usd,
                                   row.ri_upfront_usd, int(row.term_years),
                                   Decimal(runtime) / 100)
            records.append(dict(runtime_percent=runtime, option=label,
                                ri_cost=m['ri_annualized_cost_usd'],
                                od_cost=m['on_demand_annual_cost_usd']))
    return pd.DataFrame(records)
