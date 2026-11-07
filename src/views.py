"""Display only: all financial measures arrive already calculated."""
from decimal import Decimal
import pandas as pd
import streamlit as st
from src.pair_rates import PRICE_COLUMNS
from src.scenario import MONEY, RESULT_COLUMNS
from src.filter_rates import PAYMENTS

def usd(value):
    return f"${value:,.2f}"

def hourly(value):
    if value == 0: return "$0"
    digits = max(4, -value.adjusted() + 2)
    return f"${value:,.{digits}f}"

def percent(value, reference=None):
    amount = value * 100
    digits = 2
    while reference is not None and digits < 30:
        shown = Decimal(f"{amount:.{digits}f}")
        ref = reference * 100
        if (shown > ref) == (amount > ref) and (shown < ref) == (amount < ref):
            break
        digits += 1
    return f"{amount:.{digits}f}%"

def handoff_error(results, instance_type):
    required = PRICE_COLUMNS + RESULT_COLUMNS
    if not set(required) <= set(results.columns): return "Missing result columns."
    if not results.empty:
        if results[required].isna().any().any(): return "Missing result values."
        if not results.instance_type.eq(instance_type).all(): return "Results contain another instance."
        if any(results[c].nunique() != 1 for c in ["price_list_version","publication_date","on_demand_hourly_usd"]):
            return "Mixed source metadata or On-Demand rates."
        if not results.term_years.isin([1,3]).all() or not results.purchase_option.isin(PAYMENTS).all():
            return "Unsupported term or payment option."
        for field in MONEY + RESULT_COLUMNS[:-1]:
            if not all(isinstance(v,Decimal) and v.is_finite() for v in results[field]):
                return "Invalid numeric result values."
    return None

def render_comparison(results: pd.DataFrame, instance_type: str, utilization: Decimal) -> None:
    error = handoff_error(results, instance_type)
    if error:
        st.error(f"Result handoff error: {error}")
        return
    if results.empty:
        st.info("No valid Reserved Instance options are available for this selection.")
        return
    row = results.iloc[0]
    st.subheader(f"Purchase options · {instance_type}")
    a,b,c = st.columns([1, 1.2, 1])
    a.metric("Expected billable runtime", percent(utilization))
    b.metric("On-Demand (USD / hour)", hourly(row.on_demand_hourly_usd))
    c.metric("Instance-equivalents", "1")
    st.caption(f"AWS price snapshot · Published {row.publication_date} · Version {row.price_list_version}")
    st.caption("Annualized RI cost allocates the full commitment across its term; it is not an annual payment schedule. Upfront payment is shown separately.")
    for years, title in [(1,"One-year commitment"),(3,"Three-year commitment")]:
        st.markdown(f"### {title}")
        term = results[results.term_years.eq(years)].copy()
        if term.empty:
            st.info("No valid options are available for this term.")
            continue
        term["_order"] = term.purchase_option.map({p:i for i,p in enumerate(PAYMENTS)})
        term = term.sort_values("_order")
        display = []
        for r in term.itertuples():
            display.append({
                "Purchase option": r.purchase_option,
                "Upfront payment (USD)": usd(r.ri_upfront_usd),
                "Recurring RI / h": hourly(r.ri_hourly_usd),
                "Effective RI / h": hourly(r.effective_ri_hourly_usd),
                "Annualized RI cost (USD)": usd(r.ri_annualized_cost_usd),
                "On-Demand annual cost (USD)": usd(r.on_demand_annual_cost_usd),
                "Annual savings vs OD (USD)": usd(r.annual_savings_vs_od_usd),
                "Break-even runtime": percent(r.break_even_utilization,utilization),
                "Comparison status": r.comparison_status,
            })
        st.caption(f"On-Demand baseline: {usd(row.on_demand_annual_cost_usd)} per modeled year. All cost and savings columns below are in USD.")
        summary_columns = ["Purchase option", "Upfront payment (USD)",
                           "Annualized RI cost (USD)", "Annual savings vs OD (USD)",
                           "Break-even runtime"]
        st.dataframe(pd.DataFrame(display), hide_index=True, width="stretch",
                     column_order=summary_columns,
                     column_config={
                         "Purchase option": st.column_config.TextColumn("Payment", width="medium"),
                         "Upfront payment (USD)": st.column_config.TextColumn("Upfront ($)", width="small"),
                         "Annualized RI cost (USD)": st.column_config.TextColumn("RI / year ($)", width="small"),
                         "Annual savings vs OD (USD)": st.column_config.TextColumn("Savings / year ($)", width="small"),
                         "Break-even runtime": st.column_config.TextColumn("Break-even (%)", width="small"),
                     })
        with st.expander(f"{years}-year payment details and comparison status"):
            st.table(pd.DataFrame(display)[["Purchase option", "Recurring RI / h",
                     "Effective RI / h", "Comparison status"]].rename(columns={
                         "Purchase option": "Payment", "Recurring RI / h": "Recurring RI ($ / hour)",
                         "Effective RI / h": "Effective RI ($ / hour)",
                         "Comparison status": "Comparison"}))
        if term.annual_savings_vs_od_usd.lt(0).any():
            st.caption("Negative savings mean a modeled cost increase versus On-Demand at the entered runtime.")
        if term.break_even_utilization.gt(1).any():
            st.warning("A break-even runtime above 100% is unattainable within the modeled runtime range.")
    st.info("One-year and three-year commitments cover different periods. Annualization does not make their duration or workload risks equivalent.")
