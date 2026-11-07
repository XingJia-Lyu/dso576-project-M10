"""Decision support and interactive runtime sensitivity."""
import altair as alt
import pandas as pd
import streamlit as st
from src.decision import eligible_options, sensitivity_table
from src.views import usd, percent


def render_decision_support(results, utilization):
    if results.empty:
        return
    st.divider()
    st.subheader('Plan within your constraints')
    st.caption('For one instance-equivalent. These filters affect the shortlist and chart below; the full comparison above remains available.')
    a, b = st.columns(2)
    max_years = a.selectbox('Maximum acceptable commitment (years)', [1, 3], index=1, key='max_years')
    budget = b.number_input('Maximum upfront payment (USD)', min_value=0.0,
                            value=float(results.ri_upfront_usd.max()), step=100.0,
                            key='max_upfront')
    eligible = eligible_options(results, max_years, budget)
    if eligible.empty:
        st.info('No RI options meet both constraints. On-Demand remains a baseline without an RI upfront payment or term commitment. Adjust the constraints to explore more options.')
        return
    st.dataframe(pd.DataFrame([{
        'Term (years)': int(r.term_years), 'Payment': r.purchase_option,
        'Upfront (USD)': usd(r.ri_upfront_usd),
        'Annualized RI cost (USD)': usd(r.ri_annualized_cost_usd),
        'Annual savings vs OD (USD)': usd(r.annual_savings_vs_od_usd),
        'Break-even runtime': percent(r.break_even_utilization, utilization)
    } for r in eligible.itertuples() ]), hide_index=True, width='stretch', column_config={
        'Term (years)': st.column_config.NumberColumn('Years', width='small'),
        'Payment': st.column_config.TextColumn('Payment', width='medium'),
        'Upfront (USD)': st.column_config.TextColumn('Upfront ($)', width='small'),
        'Annualized RI cost (USD)': st.column_config.TextColumn('RI / year ($)', width='small'),
        'Annual savings vs OD (USD)': st.column_config.TextColumn('Savings / year ($)', width='small'),
        'Break-even runtime': st.column_config.TextColumn('Break-even (%)', width='small'),
    })
    # Compare within each term: annualization alone cannot rank commitment risk.
    for years in sorted(eligible.term_years.unique()):
        group = eligible.loc[eligible.term_years.eq(years)]
        cost = group.ri_annualized_cost_usd.min()
        best = group.loc[group.ri_annualized_cost_usd.eq(cost)]
        labels = ', '.join(best.purchase_option)
        saving = best.iloc[0].annual_savings_vs_od_usd
        if saving > 0:
            st.success(f'{years}-year term: {labels} has the lowest modeled RI cost among eligible options, saving {usd(saving)} per modeled year versus On-Demand at {percent(utilization)} runtime.')
        elif saving == 0:
            st.info(f'{years}-year term: {labels} ties On-Demand at the entered runtime.')
        else:
            st.warning(f'{years}-year term: even the lowest-cost eligible RI option ({labels}) costs {usd(-saving)} more per modeled year than On-Demand at the entered runtime.')
    st.caption('These are conditional cost comparisons, not purchase recommendations. Validate workload duration, negotiated prices and existing commitments. Compare one-year and three-year risks separately.')
    st.subheader('What if expected runtime changes?')
    st.caption('Annualized compute cost (USD) across 0–100% billable runtime. RI charges stay payable even when runtime falls. Hover for values; use the legend to identify each option.')
    exact = sensitivity_table(eligible)
    lines = []
    for r in exact.itertuples():
        lines.append({'Runtime (%)': r.runtime_percent, 'Annualized cost (USD)': float(r.ri_cost), 'Option': r.option})
    od = exact.drop_duplicates('runtime_percent')
    for r in od.itertuples():
        lines.append({'Runtime (%)': r.runtime_percent, 'Annualized cost (USD)': float(r.od_cost), 'Option': 'On-Demand'})
    base = alt.Chart(pd.DataFrame(lines)).mark_line().encode(
        x=alt.X('Runtime (%):Q', scale=alt.Scale(domain=[0, 100])),
        y=alt.Y('Annualized cost (USD):Q', scale=alt.Scale(zero=True)),
        color=alt.Color('Option:N'),
        tooltip=['Option:N', 'Runtime (%):Q', alt.Tooltip('Annualized cost (USD):Q', format=',.2f')])
    points = pd.DataFrame([{'Runtime (%)': float(r.break_even_utilization * 100),
                            'Annualized cost (USD)': float(r.ri_annualized_cost_usd),
                            'Option': f'{r.term_years}y · {r.purchase_option}'}
                           for r in eligible.itertuples() if 0 <= r.break_even_utilization <= 1])
    chart = base
    if not points.empty:
        chart = chart + alt.Chart(points).mark_point(size=85, filled=True).encode(
            x='Runtime (%):Q', y='Annualized cost (USD):Q', color='Option:N',
            tooltip=['Option:N', alt.Tooltip('Runtime (%):Q', title='Break-even runtime (%)', format='.2f')])
    rule = alt.Chart(pd.DataFrame({'Runtime (%)': [float(utilization * 100)]})).mark_rule(strokeDash=[5, 4], color='#475569').encode(x='Runtime (%):Q')
    st.altair_chart((chart + rule).properties(height=370), width="stretch")
    st.caption('Dots mark attainable break-even points; the dashed line marks your entered runtime. Exact break-even values appear in the table. Curves use annualized costs; three-year charges still commit you for three years.')
