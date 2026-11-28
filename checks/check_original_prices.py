"""R5 reference: original AWS CSV -> exact expected results -> observed comparison.

No application imports. All reference arithmetic uses exact rational numbers.
The separately captured app values are read only AFTER building the reference.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SCOPE = {
    "Product Family": "Compute Instance", "Region Code": "us-east-1",
    "Operating System": "Linux", "Tenancy": "Shared", "CapacityStatus": "Used",
    "Pre Installed S/W": "NA", "MarketOption": "OnDemand",
    "License Model": "No License required",
}
PAYMENTS = {"NoUpfront": "No Upfront", "PartialUpfront": "Partial Upfront",
            "AllUpfront": "All Upfront"}
FIELDS = ("ri_annualized_cost_usd", "on_demand_annual_cost_usd",
          "annual_savings_vs_od_usd", "break_even_utilization")
GRID = tuple(range(101))
CONSTRAINT_RUNTIMES = (0, 50, 80, 100)


class AuditError(ValueError):
    pass


def rational(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("nonfinite number")
        return Fraction(number)
    except Exception as exc:
        raise AuditError(f"Invalid number: {value!r}") from exc


def text(value):
    if isinstance(value, Fraction):
        with localcontext() as ctx:
            ctx.prec = 60
            return str(Decimal(value.numerator) / Decimal(value.denominator))
    if isinstance(value, (list, tuple, set, dict)):
        return json.dumps(sorted(value) if isinstance(value, set) else value,
                          sort_keys=True, default=text)
    return str(value)


def usd(value):
    with localcontext() as ctx:
        ctx.prec = 60
        number = Decimal(value.numerator) / Decimal(value.denominator)
        return f"${number:,.2f}"


def fingerprint(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_original(path):
    """Stream the untouched publisher file; reject ambiguous in-scope components."""
    path = Path(path)
    od, groups = defaultdict(list), defaultdict(list)
    inspected_records = []
    raw_rows = retained = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            metadata = dict(next(reader) for _ in range(5))
            header = next(reader)
        except Exception as exc:
            raise AuditError("Invalid five-row AWS metadata/header") from exc
        required = set(SCOPE) | {
            "Instance Type", "SKU", "OfferTermCode", "RateCode", "TermType",
            "OfferingClass", "LeaseContractLength", "PurchaseOption", "Unit",
            "Currency", "PricePerUnit", "StartingRange", "EndingRange",
        }
        if len(header) != len(set(header)) or not required <= set(header):
            raise AuditError("Missing or duplicate original CSV columns")
        if not metadata.get("Version") or not metadata.get("Publication Date"):
            raise AuditError("Missing original publication/version metadata")
        for values in reader:
            raw_rows += 1
            if len(values) != len(header):
                raise AuditError(f"Malformed original row {raw_rows}")
            row = dict(zip(header, values))
            if not row["Instance Type"].startswith("c6i."):
                continue
            if not all(row[k] == v for k, v in SCOPE.items()):
                continue
            term = row["TermType"]
            if term not in {"OnDemand", "Reserved"}:
                continue
            if term == "Reserved" and row["OfferingClass"] != "standard":
                continue
            retained += 1
            inspected_records.append(row.copy())
            amount = rational(row["PricePerUnit"])
            if amount < 0 or row["Currency"] != "USD" or not row["SKU"] or not row["OfferTermCode"]:
                raise AuditError(f"Unsupported amount/currency/key at row {raw_rows}")
            if row["Unit"] == "Hrs":
                if rational(row["StartingRange"]) != 0 or row["EndingRange"] != "Inf":
                    raise AuditError(f"Unsupported hourly range at row {raw_rows}")
            elif row["Unit"] == "Quantity" and term == "Reserved":
                if row["StartingRange"] or row["EndingRange"]:
                    raise AuditError(f"Unsupported upfront range at row {raw_rows}")
            else:
                raise AuditError(f"Unsupported rate unit at row {raw_rows}")
            row["_amount"] = amount
            row["_record_number"] = raw_rows
            if term == "OnDemand":
                if amount <= 0:
                    raise AuditError("On-Demand baseline must be positive")
                od[row["SKU"]].append(row)
            else:
                groups[(row["SKU"], row["OfferTermCode"])].append(row)
    options = {}
    for (sku, offer), rows in groups.items():
        hourly = [r for r in rows if r["Unit"] == "Hrs"]
        quantity = [r for r in rows if r["Unit"] == "Quantity"]
        attributes = {(r["Instance Type"], r["LeaseContractLength"].replace(" ", ""),
                       r["PurchaseOption"].replace(" ", "")) for r in rows}
        if len(hourly) != 1 or len(quantity) > 1 or len(attributes) != 1 or len(od[sku]) != 1:
            raise AuditError(f"Ambiguous or incomplete original components: {sku}/{offer}")
        instance, lease, payment = next(iter(attributes))
        if lease not in {"1yr", "3yr"} or payment not in PAYMENTS:
            raise AuditError(f"Unsupported original term/payment: {sku}/{offer}")
        if od[sku][0]["Instance Type"] != instance:
            raise AuditError("On-Demand/Reserved product mismatch")
        if payment == "NoUpfront":
            if quantity and quantity[0]["_amount"] != 0:
                raise AuditError("No Upfront has a nonzero upfront component")
        elif len(quantity) != 1:
            raise AuditError("Partial/All Upfront requires an upfront component")
        key = (instance, int(lease[0]), PAYMENTS[payment])
        if key in options:
            raise AuditError(f"Multiple product/offer keys for {key}")
        options[key] = {
            "on_demand_hourly_usd": od[sku][0]["_amount"],
            "ri_upfront_usd": quantity[0]["_amount"] if quantity else Fraction(0),
            "ri_hourly_usd": hourly[0]["_amount"],
            "years": key[1], "sku": sku, "offer_term_code": offer,
            "rate_codes": [r["RateCode"] for r in [od[sku][0], *rows]],
            "original_record_numbers": [r["_record_number"] for r in [od[sku][0], *rows]],
        }
    if not options:
        raise AuditError("No valid in-scope options in original file")
    return {"options": options, "inspected_records": inspected_records,
            "metadata": metadata, "raw_rows": raw_rows,
            "raw_columns": len(header), "retained_components": retained,
            "filename": path.name, "size_bytes": path.stat().st_size,
            "sha256": fingerprint(path)}


def measures(option, utilization):
    p, h, f = (option[k] for k in ("on_demand_hourly_usd", "ri_hourly_usd", "ri_upfront_usd"))
    years = option["years"]
    hours = 365 * 24 * years
    commitment = f + h * hours
    annual = commitment / years
    demand = p * 365 * 24 * utilization
    saving = demand - annual
    return {
        "effective_ri_hourly_usd": commitment / hours,
        "ri_annualized_cost_usd": annual, "on_demand_annual_cost_usd": demand,
        "annual_savings_vs_od_usd": saving,
        "break_even_utilization": commitment / (p * hours),
        "comparison_status": "RI lower modeled cost" if saving > 0 else
                             "On-Demand lower modeled cost" if saving < 0 else "Break-even",
    }


def option_key(row):
    return (row["instance_type"], int(row["term_years"]), row["purchase_option"])


def budgets(options, instance):
    amounts = {v["ri_upfront_usd"] for k, v in options.items() if k[0] == instance}
    return sorted({Fraction(0), *amounts, *(x - Fraction(1, 100) for x in amounts if x >= Fraction(1, 100))})


def audit(source, observed, require_complete=True):
    options = source["options"]
    records, mismatches = [], []
    counts = Counter()
    def check(section, key, field, expected, actual):
        counts[section] += 1
        if isinstance(expected, Fraction):
            try:
                tolerance = Fraction("1e-8" if section == "chart" else
                                     "1e-24" if field == "effective_ri_hourly_usd" else "1e-20")
                equal = abs(expected - rational(actual)) <= tolerance
            except AuditError:
                equal = False
        else:
            equal = expected == actual
        record = dict(section=section, selection=text(key), field=field,
                      expected=text(expected), observed=text(actual), match=equal)
        records.append(record)
        if not equal:
            mismatches.append(record)
    check("source", "snapshot", "version", source["metadata"]["Version"], observed.get("price_list_version"))
    check("source", "snapshot", "publication", source["metadata"]["Publication Date"], observed.get("publication_date"))
    prices = observed.get("prices", [])
    keys = [option_key(r) for r in prices]
    check("prices", "all", "option_keys", set(options), set(keys))
    check("prices", "all", "unique_option_keys", len(keys), len(set(keys)))
    for row in prices:
        key = option_key(row)
        if key not in options:
            continue
        reference = options[key] | measures(options[key], Fraction(0))
        for field in ("on_demand_hourly_usd", "ri_upfront_usd", "ri_hourly_usd", "effective_ri_hourly_usd"):
            check("prices", key, field, reference[field], row.get(field))
    coverage = {name: [] for name in ("scenarios", "sensitivity", "constraints", "ui")}
    for row in observed.get("scenarios", []):
        key, percent = tuple(row["key"]), row["runtime_percent"]
        coverage["scenarios"].append((key, percent))
        if key not in options:
            check("scenarios", key, "known_option", True, False)
            continue
        reference = measures(options[key], Fraction(str(percent)) / 100)
        for field in (*FIELDS, "comparison_status"):
            check("scenarios", (*key, percent), field, reference[field], row.get(field))
    for row in observed.get("sensitivity", []):
        key, percent = tuple(row["key"]), row["runtime_percent"]
        coverage["sensitivity"].append((key, percent))
        if key not in options:
            check("sensitivity", key, "known_option", True, False)
            continue
        reference = measures(options[key], Fraction(str(percent)) / 100)
        for field, observed_field in [("ri_annualized_cost_usd", "ri_cost"), ("on_demand_annual_cost_usd", "od_cost")]:
            check("sensitivity", (*key, percent), field, reference[field], row.get(observed_field))
    for row in observed.get("constraints", []):
        instance, years, budget = row["instance_type"], row["max_years"], rational(row["max_upfront"])
        selection = (instance, row["runtime_percent"], years, budget)
        coverage["constraints"].append(selection)
        expected = {k for k, o in options.items() if k[0] == instance and k[1] <= years and o["ri_upfront_usd"] <= budget}
        actual_keys = [tuple(k) for k in row["eligible"]]
        check("constraints", selection, "eligible_options", expected, set(actual_keys))
        check("constraints", selection, "unique_eligible_options", len(actual_keys), len(set(actual_keys)))
    for row in observed.get("ui", []):
        instance, percent = row["instance_type"], row["runtime_percent"]
        coverage["ui"].append((instance, percent, row["max_years"], rational(row["max_upfront"])))
        selection = (instance, percent, row["max_years"], row["max_upfront"])
        wanted = {k: o for k, o in options.items() if k[0] == instance}
        actual_rows = row.get("rows", [])
        actual_keys = [(instance, int(r["term_years"]), r["Purchase option"]) for r in actual_rows]
        check("ui", selection, "displayed_keys", set(wanted), set(actual_keys))
        check("ui", selection, "duplicate_rows", len(actual_keys), len(set(actual_keys)))
        for display in actual_rows:
            key = (instance, int(display["term_years"]), display["Purchase option"])
            if key not in wanted:
                continue
            values = measures(wanted[key], Fraction(str(percent))/100)
            for label, field in [("Annualized RI cost (USD)", FIELDS[0]),
                                 ("On-Demand annual cost (USD)", FIELDS[1]),
                                 ("Annual savings vs OD (USD)", FIELDS[2])]:
                check("ui", (*key, percent), label, usd(values[field]), display.get(label))
            check("ui", (*key, percent), "Comparison status", values["comparison_status"], display.get("Comparison status"))
        eligible = {k: o for k, o in wanted.items() if k[1] <= row["max_years"] and o["ri_upfront_usd"] <= rational(row["max_upfront"])}
        check("ui", selection, "shortlist_keys", set(eligible), {tuple(k) for k in row["shortlist_keys"]})
        # Independently check the actual serialized chart datasets and encodings.
        layers = row.get("chart_spec", {}).get("layer", [])
        datasets = row.get("chart_datasets", {})
        marks = [layer.get("mark", {}).get("type") for layer in layers]
        labels = {f"{k[1]}y · {k[2]}": k for k in eligible}
        attainable = {label for label, k in labels.items()
                      if 0 <= measures(eligible[k], Fraction(0))[FIELDS[3]] <= 1}
        check("chart", selection, "marks", ["line", *(["point"] if attainable else []), "rule"], marks)
        expected_lines = {(f"{k[1]}y · {k[2]}", u) for k in eligible for u in GRID}
        expected_lines |= {("On-Demand", u) for u in GRID}
        line_keys, point_keys, marker_count = [], [], 0
        for layer in layers:
            mark = layer.get("mark", {}).get("type")
            data = datasets.get(layer.get("data", {}).get("name"), [])
            enc = layer.get("encoding", {})
            check("chart", selection, f"{mark}_x_field", "Runtime (%)", enc.get("x", {}).get("field"))
            if mark in {"line", "point"}:
                check("chart", selection, f"{mark}_y_field", "Annualized cost (USD)", enc.get("y", {}).get("field"))
            for item in data:
                if mark == "rule":
                    marker_count += 1
                    check("chart", selection, "runtime_marker", Fraction(str(percent)), item.get("Runtime (%)"))
                    continue
                label, u = item.get("Option"), item.get("Runtime (%)")
                if label == "On-Demand" and mark == "line":
                    o = next(iter(eligible.values()))
                    value = measures(o, rational(u)/100)[FIELDS[1]]
                elif label in labels:
                    o = eligible[labels[label]]
                    m = measures(o, Fraction(0))
                    value = m[FIELDS[0]]
                    if mark == "point":
                        point_keys.append(label)
                        check("chart", (selection, label), "break_even_dot", m[FIELDS[3]]*100, u)
                else:
                    check("chart", selection, "known_series", True, False)
                    continue
                if mark == "line":
                    line_keys.append((label, u))
                check("chart", (selection, label, u), "annual_cost", value, item.get("Annualized cost (USD)"))
        check("chart", selection, "line_coverage", expected_lines, set(line_keys))
        check("chart", selection, "unique_lines", len(line_keys), len(set(line_keys)))
        check("chart", selection, "dot_coverage", attainable, set(point_keys))
        check("chart", selection, "unique_dots", len(point_keys), len(set(point_keys)))
        check("chart", selection, "runtime_marker_count", 1, marker_count)
        for years in sorted({k[1] for k in eligible}):
            term = {k: measures(o, Fraction(str(percent))/100) for k,o in eligible.items() if k[1] == years}
            cost = min(v[FIELDS[0]] for v in term.values())
            best = {k[2] for k,v in term.items() if v[FIELDS[0]] == cost}
            pick = next((p for p in row["picks"] if p["term_years"] == years), {})
            saving = next(v[FIELDS[2]] for v in term.values() if v[FIELDS[0]] == cost)
            kind = "success" if saving > 0 else "warning" if saving < 0 else "info"
            check("ui", (*selection, years), "lowest_cost_payment", best, set(pick.get("payments", [])))
            check("ui", (*selection, years), "message_kind", kind, pick.get("kind"))
            if saving:
                check("ui", (*selection, years), "message_amount", usd(abs(saving)), pick.get("amount"))
    if require_complete:
        expected_grid = {(key, u) for key in options for u in GRID}
        for name in ("scenarios", "sensitivity"):
            check("coverage", name, "coverage", expected_grid, set(coverage[name]))
            check("coverage", name, "unique_records", len(coverage[name]), len(set(coverage[name])))
        instances = sorted({k[0] for k in options})
        expected_constraints = {(i, u, y, b) for i in instances for u in CONSTRAINT_RUNTIMES
                                for y in (1, 3) for b in budgets(options, i)}
        check("coverage", "constraints", "coverage", expected_constraints, set(coverage["constraints"]))
        check("coverage", "constraints", "unique_records", len(coverage["constraints"]), len(set(coverage["constraints"])))
        expected_ui = expected_constraints
        check("coverage", "ui", "coverage", expected_ui, set(coverage["ui"]))
        check("coverage", "ui", "unique_records", len(coverage["ui"]), len(set(coverage["ui"])))
    return {"mismatch_count": len(mismatches), "comparison_count": len(records),
            "comparisons_by_section": dict(counts), "mismatches": mismatches,
            "records": records, "coverage_counts": {k: len(v) for k,v in coverage.items()}}


def download_original(path, version):
    path = Path(path)
    receipt = path.with_suffix(path.suffix + ".receipt.json")
    if path.exists():
        if not receipt.is_file():
            raise AuditError("Existing raw file has no download receipt; refusing to overwrite it")
        info = json.loads(receipt.read_text())
        if info["sha256"] != fingerprint(path) or info["version"] != version:
            raise AuditError("Existing raw source/receipt mismatch")
        return info
    url = f"https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/{version}/us-east-1/index.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                digest = hashlib.sha256()
                size = 0
                while block := response.read(1024 * 1024):
                    output.write(block)
                    digest.update(block)
                    size += len(block)
        info = {"version": version, "source_url": url, "filename": path.name,
                "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
                "size_bytes": size, "sha256": digest.hexdigest()}
        temporary.replace(path)
        receipt.write_text(json.dumps(info, indent=2) + "\n")
        return info
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--observed", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT/"checks/r5-results")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--download-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.download:
            info = download_original(args.raw, args.source_version)
            print(f"Original CSV: {info['filename']} ({info['size_bytes']} bytes)")
        if args.download_only:
            return 0
        source = read_original(args.raw)
        if source["metadata"]["Version"] != args.source_version:
            raise AuditError("Original CSV does not have the requested source version")
        # The original-source reconstruction above precedes all observed-app reads.
        if not args.observed:
            raise AuditError("--observed is required for a comparison")
        opener = gzip.open if str(args.observed).endswith(".gz") else open
        with opener(args.observed, "rt", encoding="utf-8") as handle:
            observed = json.load(handle)
        result = audit(source, observed)
        receipt_path = args.raw.with_suffix(args.raw.suffix + ".receipt.json")
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
        if not receipt or receipt.get("sha256") != source["sha256"] or not receipt.get("downloaded_at_utc"):
            raise AuditError("Full audit requires the original source's matching download receipt")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        with (args.output_dir/"original-records.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=source["inspected_records"][0].keys(), lineterminator="\n")
            writer.writeheader()
            writer.writerows(source["inspected_records"])
        provenance = []
        for key, option in sorted(source["options"].items()):
            provenance.append({"instance_type": key[0], "term_years": key[1],
                               "purchase_option": key[2],
                               **option})
        (args.output_dir/"original_options.json").write_text(json.dumps(provenance, indent=2, default=text)+"\n")
        with gzip.open(args.output_dir/"comparisons.csv.gz", "wt", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["section", "selection", "field", "expected", "observed", "match"])
            writer.writeheader()
            writer.writerows(result.pop("records"))
        provenance = {k:v for k,v in source.items() if k not in {"options", "inspected_records"}}
        result.update(source=provenance, download_receipt=receipt,
                      observed_commit=observed.get("app_commit"),
                      observed_file_sha256=fingerprint(args.observed),
                      observed_capture_time=observed.get("captured_at_utc"),
                      prepared_price_sha256=observed.get("price_table_sha256"),
                      option_count=len(source["options"]),
                      limitations=["101 integer runtimes, not all real-valued inputs",
                                   "Declared budget boundaries and UI states, not every interaction",
                                   "Local checked-out app; live deployment not authenticated",
                                   "Constant-price public-price model; not actual company savings"])
        (args.output_dir/"summary.json").write_text(json.dumps(result, indent=2) + "\n")
        print(f"Source version: {source['metadata']['Version']}; {source['raw_rows']:,} original rows")
        print(f"Options independently reconstructed: {len(source['options'])}")
        print(f"Recorded checks: {result['comparison_count']}; mismatches: {result['mismatch_count']}")
        print("Coverage: " + json.dumps(result["coverage_counts"], sort_keys=True))
        print("PASS" if not result["mismatch_count"] else "FAIL; see summary.json")
        return 1 if result["mismatch_count"] else 0
    except (AuditError, OSError, ValueError, KeyError) as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
