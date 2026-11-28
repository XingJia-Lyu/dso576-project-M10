"""Capture observations only. The independent reference never imports this file.

Uses the real app functions and local Streamlit AppTest, without patching prices,
formulas, or widgets. Run again after changing app code or its prepared snapshot.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.load_data import load_price_options
from src.scenario import calculate_scenario
from src.decision import eligible_options, sensitivity_table


def key(row):
    return [row.instance_type, int(row.term_years), row.purchase_option]


def capture_ui(instances, prices):
    from streamlit.testing.v1 import AppTest
    import pyarrow as pa
    app = AppTest.from_file(str(ROOT / "dashboard.py"), default_timeout=30).run()
    records = []
    for instance in instances:
        app.selectbox(key="instance_type").select(instance).run()
        amounts = {Decimal(v) for v in prices.loc[prices.instance_type.eq(instance), "ri_upfront_usd"]}
        caps = sorted({Decimal(0), *amounts, *(v-Decimal(".01") for v in amounts if v >= Decimal(".01"))})
        selections = [(runtime, years, cap) for runtime in (0, 50, 80, 100)
                      for years in (1, 3) for cap in caps]
        for runtime, years_limit, cap in selections:
            app.number_input(key="runtime_percent").set_value(runtime)
            app.selectbox(key="max_years").select(years_limit)
            app.number_input(key="max_upfront").set_value(float(cap))
            app.run()
            if len(app.exception):
                raise RuntimeError(f"App exception: {app.exception}")
            if len(app.dataframe) != 3:
                raise RuntimeError("Expected two comparison tables and one shortlist")
            displayed = []
            for years, element in zip((1, 3), app.dataframe[:2]):
                for row in element.value.to_dict("records"):
                    displayed.append({"term_years": years, **row})
            shortlist = [[instance, int(r["Term (years)"]), r["Payment"]]
                         for r in app.dataframe[2].value.to_dict("records")]
            picks = []
            for kind in ("success", "warning", "info"):
                for element in getattr(app, kind):
                    message = element.value
                    match = re.match(r"([13])-year term: (.*)", message)
                    if not match:
                        continue
                    years, body = int(match[1]), match[2]
                    if kind == "success":
                        labels = body.split(" has the lowest modeled RI cost", 1)[0]
                    elif kind == "warning":
                        labels = body.split("RI option (", 1)[1].split(") costs ", 1)[0]
                    else:
                        labels = body.split(" ties On-Demand", 1)[0]
                    amount = re.search(r"\$[\d,]+\.\d{2}", body)
                    picks.append({"term_years": years, "kind": kind,
                                  "payments": labels.split(", "),
                                  "amount": amount.group() if amount else None,
                                  "message": message})
            charts = app.get("vega_lite_chart")
            if len(charts) != 1:
                raise RuntimeError("Expected one sensitivity chart")
            # Record the actual Vega-Lite specification, not just the helper table.
            spec = json.loads(charts[0].proto.spec)
            datasets = {d.name: pa.ipc.open_stream(d.data.data).read_all().to_pylist()
                        for d in charts[0].proto.datasets}
            records.append({"instance_type": instance, "runtime_percent": runtime,
                            "max_years": years_limit, "max_upfront": str(cap), "rows": displayed,
                            "shortlist_keys": shortlist, "picks": picks,
                            "chart_spec": spec, "chart_datasets": datasets})
        print(f"Captured local UI: {instance}, {len(selections)} runtime/term/budget states", flush=True)
    return records


def capture():
    path = ROOT / "data/processed/c6i_price_options.parquet"
    prices = load_price_options(path)
    instances = sorted(prices.instance_type.unique())
    observations = {
        "schema_version": 1,
        "app_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "price_list_version": str(prices.price_list_version.iloc[0]),
        "publication_date": str(prices.publication_date.iloc[0]),
        "price_table_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "app_source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [ROOT/"dashboard.py", *sorted((ROOT/"src").glob("*.py"))]},
        "prices": prices.to_dict("records"), "scenarios": [],
        "constraints": [], "sensitivity": [],
    }
    for instance in instances:
        upfronts = {Decimal(v) for v in prices.loc[prices.instance_type.eq(instance), "ri_upfront_usd"]}
        limits = sorted({Decimal(0), *upfronts, *(v-Decimal(".01") for v in upfronts if v >= Decimal(".01"))})
        for runtime in range(101):
            results = calculate_scenario(prices, instance, Decimal(runtime)/100)
            for row in results.itertuples():
                observations["scenarios"].append({
                    "key": key(row), "runtime_percent": runtime,
                    **{field: str(getattr(row, field)) for field in
                       ("ri_annualized_cost_usd", "on_demand_annual_cost_usd",
                        "annual_savings_vs_od_usd", "break_even_utilization", "comparison_status")}})
            if runtime in (0, 50, 80, 100):
                for years in (1, 3):
                    for cap in limits:
                        selected = eligible_options(results, years, cap)
                        observations["constraints"].append({
                            "instance_type": instance, "runtime_percent": runtime,
                            "max_years": years, "max_upfront": str(cap),
                            "eligible": [key(row) for row in selected.itertuples()]})
        for row in sensitivity_table(results).itertuples():
            years, payment = row.option.split("y · ", 1)
            observations["sensitivity"].append({
                "key": [instance, int(years), payment], "runtime_percent": row.runtime_percent,
                "ri_cost": str(row.ri_cost), "od_cost": str(row.od_cost)})
    observations["ui"] = capture_ui(instances, prices)
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"checks/r5-observed.json.gz")
    args = parser.parse_args()
    observed = capture()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.output, "wt", encoding="utf-8") as handle:
        json.dump(observed, handle, sort_keys=True)
    print("App observations: " + json.dumps({k:len(observed[k]) for k in
          ("prices", "scenarios", "constraints", "sensitivity", "ui")}, sort_keys=True))
    print(f"Saved: {args.output.name}")


if __name__ == "__main__":
    main()
