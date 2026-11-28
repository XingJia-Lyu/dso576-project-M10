"""Tests for the independent verifier, separate from the app's calculations."""
import ast
import copy
import csv
from fractions import Fraction as F
from pathlib import Path

import pytest

from checks.check_original_prices import AuditError, audit, measures, read_original


def raw_file(tmp_path, *, corrupt=None):
    common = {
        "Product Family": "Compute Instance", "Region Code": "us-east-1",
        "Operating System": "Linux", "Tenancy": "Shared", "CapacityStatus": "Used",
        "Pre Installed S/W": "NA", "MarketOption": "OnDemand",
        "License Model": "No License required", "Instance Type": "c6i.large",
        "SKU": "sku", "Currency": "USD", "OfferingClass": "standard",
        "LeaseContractLength": "1yr", "StartingRange": "0", "EndingRange": "Inf",
    }
    rows = []
    for term, offer, payment, unit, price in [
        ("OnDemand", "od", "", "Hrs", ".20"),
        ("Reserved", "no", "No Upfront", "Hrs", ".12"),
        ("Reserved", "all", "All Upfront", "Hrs", "0"),
        ("Reserved", "all", "All Upfront", "Quantity", "876"),
    ]:
        rows.append(common | {"TermType": term, "OfferTermCode": offer,
                              "PurchaseOption": payment, "Unit": unit,
                              "PricePerUnit": price, "RateCode": f"{offer}-{unit}"})
        if unit == "Quantity":
            rows[-1].update(StartingRange="", EndingRange="")
    if corrupt:
        corrupt(rows)
    path = tmp_path / "original.csv"
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows([
            ["FormatVersion", "v1.0"], ["Disclaimer", "fixture"],
            ["Publication Date", "2026-10-15T19:13:16Z"],
            ["Version", "20261015191316"], ["OfferCode", "AmazonEC2"],
        ])
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def observations():
    return {
        "schema_version": 1,
        "price_list_version": "20261015191316",
        "publication_date": "2026-10-15T19:13:16Z",
        "prices": [
            {"instance_type": "c6i.large", "term_years": 1,
             "purchase_option": "No Upfront", "on_demand_hourly_usd": ".20",
             "ri_upfront_usd": "0", "ri_hourly_usd": ".12",
             "effective_ri_hourly_usd": ".12"},
            {"instance_type": "c6i.large", "term_years": 1,
             "purchase_option": "All Upfront", "on_demand_hourly_usd": ".20",
             "ri_upfront_usd": "876", "ri_hourly_usd": "0",
             "effective_ri_hourly_usd": ".10"},
        ],
        "scenarios": [
            {"key": ["c6i.large", 1, "No Upfront"], "runtime_percent": 80,
             "ri_annualized_cost_usd": "1051.20",
             "on_demand_annual_cost_usd": "1401.60",
             "annual_savings_vs_od_usd": "350.40", "break_even_utilization": ".6",
             "comparison_status": "RI lower modeled cost"},
        ],
        "constraints": [], "sensitivity": [], "ui": [],
    }


def test_original_components_and_independent_formula(tmp_path):
    source = read_original(raw_file(tmp_path))
    assert len(source["options"]) == 2
    option = source["options"][("c6i.large", 1, "No Upfront")]
    result = measures(option, F(4, 5))
    assert result["ri_annualized_cost_usd"] == F("1051.20")
    assert result["annual_savings_vs_od_usd"] == F("350.40")
    assert result["break_even_utilization"] == F(3, 5)
    assert audit(source, observations(), require_complete=False)["mismatch_count"] == 0


@pytest.mark.parametrize("change", [
    lambda obs: obs["prices"][0].update(ri_hourly_usd=".11"),
    lambda obs: obs["prices"][0].update(effective_ri_hourly_usd="999"),
    lambda obs: obs["scenarios"][0].update(annual_savings_vs_od_usd="351.40"),
    lambda obs: obs["scenarios"][0].update(comparison_status="Break-even"),
    lambda obs: obs.update(price_list_version="different"),
    lambda obs: obs["prices"].pop(),
    lambda obs: obs["prices"].append(copy.deepcopy(obs["prices"][0])),
])
def test_verifier_detects_wrong_observed_data(tmp_path, change):
    source = read_original(raw_file(tmp_path))
    obs = observations()
    change(obs)
    assert audit(source, obs, require_complete=False)["mismatch_count"] > 0


@pytest.mark.parametrize("change", [
    lambda rows: rows.append(rows[1].copy()),
    lambda rows: rows.pop(),
    lambda rows: rows[1].update(StartingRange="1"),
    lambda rows: rows[3].update(StartingRange="0", EndingRange="Inf"),
    lambda rows: rows[1].update(PricePerUnit="NaN"),
    lambda rows: rows[0].update(PricePerUnit="0"),
])
def test_original_ambiguities_fail_explicitly(tmp_path, change):
    with pytest.raises(AuditError):
        read_original(raw_file(tmp_path, corrupt=change))


def test_partial_evidence_cannot_be_called_full_scope(tmp_path):
    report = audit(read_original(raw_file(tmp_path)), observations(), require_complete=True)
    assert report["mismatch_count"] > 0
    assert any("coverage" in item["field"] for item in report["mismatches"])


def test_checker_has_no_application_imports():
    path = Path(__file__).parents[1] / "checks/check_original_prices.py"
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(("src", "dashboard", "checks.capture"))
        if isinstance(node, ast.Import):
            assert not any(alias.name.startswith(("src", "dashboard")) for alias in node.names)


def ui_observation():
    # Independent hand-calculable fixture: p=.20; RI .12/h or $876 upfront.
    lines = [{"Option": label, "Runtime (%)": u, "Annualized cost (USD)": value}
             for u in range(101) for label, value in
             [("1y · No Upfront", 1051.2), ("1y · All Upfront", 876), ("On-Demand", 17.52*u)]]
    return {
        "instance_type": "c6i.large", "runtime_percent": 80, "max_years": 1,
        "max_upfront": "876", "rows": [
            {"term_years": 1, "Purchase option": payment,
             "Annualized RI cost (USD)": ri, "On-Demand annual cost (USD)": "$1,401.60",
             "Annual savings vs OD (USD)": saving, "Comparison status": "RI lower modeled cost"}
            for payment, ri, saving in [("No Upfront", "$1,051.20", "$350.40"),
                                        ("All Upfront", "$876.00", "$525.60")]],
        "shortlist_keys": [["c6i.large", 1, p] for p in ["No Upfront", "All Upfront"]],
        "picks": [{"term_years": 1, "payments": ["All Upfront"], "kind": "success", "amount": "$525.60"}],
        "chart_spec": {"layer": [
            {"mark": {"type": mark}, "data": {"name": mark}, "encoding":
             {"x": {"field": "Runtime (%)"}, "y": {"field": "Annualized cost (USD)"}}}
            for mark in ["line", "point", "rule"]]},
        "chart_datasets": {"line": lines, "point": [
            {"Option": "1y · No Upfront", "Runtime (%)": 60, "Annualized cost (USD)": 1051.2},
            {"Option": "1y · All Upfront", "Runtime (%)": 50, "Annualized cost (USD)": 876}],
            "rule": [{"Runtime (%)": 80}]},
    }


@pytest.mark.parametrize("change", [
    lambda ui: ui["chart_datasets"]["line"][0].update({"Annualized cost (USD)": 1052}),
    lambda ui: ui["chart_datasets"]["point"][0].update({"Runtime (%)": 59}),
    lambda ui: ui["chart_datasets"]["rule"][0].update({"Runtime (%)": 50}),
    lambda ui: ui["shortlist_keys"].pop(),
    lambda ui: ui["picks"][0].update(payments=["No Upfront"]),
    lambda ui: ui["picks"][0].update(amount="$526.00"),
])
def test_verifier_rejects_wrong_chart_or_decision_output(tmp_path, change):
    source, obs = read_original(raw_file(tmp_path)), observations()
    obs["ui"] = [ui_observation()]
    assert audit(source, obs, require_complete=False)["mismatch_count"] == 0
    change(obs["ui"][0])
    assert audit(source, obs, require_complete=False)["mismatch_count"] > 0
