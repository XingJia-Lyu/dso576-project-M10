"""Two controls over a cached, prepared price snapshot."""
import os
from pathlib import Path
from decimal import Decimal, InvalidOperation
import streamlit as st
from src.load_data import load_price_options, ProcessedDataError
from src.scenario import calculate_scenario
from src.views import render_comparison
from src.decision_view import render_decision_support

st.set_page_config(page_title="RI Commitment Explorer", page_icon="◈", layout="wide")

@st.cache_data(show_spinner=False)
def cached_prices(path: str, modified_ns: int, size: int):
    return load_price_options(Path(path))

def main():
    st.markdown("""<style>
    .stApp {background: #f7f9fc;}
    .block-container {padding-top: 2.4rem; max-width: 1560px;}
    [data-testid="stMetricValue"] {font-size: clamp(1.25rem, 2.5vw, 2rem);}
    [data-testid="stMetricLabel"] {white-space: normal;}
    [data-testid="stTable"] td, [data-testid="stTable"] th {white-space: normal; overflow-wrap: anywhere;}
    h1 {letter-spacing: -0.04em; color: #12223c;}
    h2, h3 {color: #203653;}
    [data-testid="stMetric"] {background: white; padding: 1rem 1.2rem; border: 1px solid #dce4ef; border-radius: 10px;}
    </style>""", unsafe_allow_html=True)
    st.caption("FINOPS / PROCUREMENT  ·  HYPOTHETICAL RIOT GAMES PLANNING")
    st.title("RI Commitment Explorer")
    st.write("Explore the cost and runtime exposure of a Standard Reserved Instance commitment.")
    st.caption("FIXED SCOPE · us-east-1 · Linux · Shared tenancy · Used capacity · No pre-installed software · No License required · OnDemand market · Non-bare-metal C6i")
    st.divider()
    path = Path(os.environ.get("RI_PRICES_PATH", str(Path(__file__).parent / "data/processed/c6i_price_options.parquet"))).resolve()
    try:
        stat = path.stat()
        prices = cached_prices(str(path), stat.st_mtime_ns, stat.st_size)
    except (OSError, ProcessedDataError) as exc:
        st.error(f"Processed prices are unavailable: {exc}. Run uv run python -m src.prepare_data")
        return
    left,right = st.columns([1,1])
    with left:
        instance = st.selectbox("Engineering-approved instance type", sorted(prices.instance_type.unique()),
                                index=None, placeholder="Select an instance type",key="instance_type")
    with right:
        runtime = st.number_input("Expected billable runtime (%)", min_value=0, max_value=100,
                                  value=80,step=1,key="runtime_percent",
                                  help="Editable assumption: the fraction of modeled hours capacity is needed. This is not CPU utilization. A continuously running machine at low CPU still incurs full On-Demand hours.")
        st.caption("Editable planning assumption · not measured from Riot's systems")
    try:
        utilization = Decimal(str(runtime)) / Decimal("100")
        if not utilization.is_finite() or not 0 <= utilization <= 1:
            raise ValueError()
    except (InvalidOperation, ValueError):
        st.error("Enter a finite expected billable runtime from 0 to 100%.")
        return
    if instance is None:
        st.info("Select an instance type to compare purchase options.")
    else:
        results = calculate_scenario(prices, instance, utilization)
        render_comparison(results, instance, utilization)
        render_decision_support(results, utilization)
    st.divider()
    with st.expander("Model assumptions and limits", expanded=True):
        st.write("One instance-equivalent; 8,760 hours per modeled year; constant published rates and expected runtime throughout each term. RI commitment charges remain payable regardless of runtime.")
        st.write("These are scenarios on an AWS published price snapshot. They exclude Riot's private discounts, credits, actual usage, existing commitments, capital costs, and future workload changes. There is no time-value-of-money adjustment, resale or exchange proceeds, storage, network, tax, or other service charges.")
    st.markdown("**Next action: investigate with internal data.** Validate expected runtime, existing commitments, and negotiated pricing before any purchasing decision. This tool does not assess instance performance requirements or establish Riot's actual bill.")

if __name__ == "__main__":
    main()
