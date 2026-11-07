"""Prepare once: source lookup, staged outputs, reports, and publication."""
import argparse
import csv
import json
import os
from pathlib import Path
import tempfile
import urllib.request
import pandas as pd
from src.filter_rates import REQUIRED_COLUMNS, filter_rates
from src.pair_rates import pair_rates

ROOT = Path(__file__).resolve().parents[1]
URL = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.csv"

def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as f:
        json.dump(value, f, indent=2)
        temp = Path(f.name)
    os.replace(temp, path)

def resolve_source(raw_path=None, refresh=False):
    if raw_path and refresh:
        raise ValueError("--refresh cannot be combined with --raw-path.")
    download = ROOT / "data/raw/ec2_us-east-1.csv"
    if not refresh:
        if raw_path:
            p = Path(raw_path).resolve()
            if not p.is_file():
                raise ValueError(f"Explicit raw source does not exist: {p}")
            return p
        for p in [ROOT.parent / "dataset_aws-price-list/data/ec2_us-east-1.csv", download]:
            if p.is_file(): return p
    download.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=download.parent, delete=False) as f:
        temporary = Path(f.name)
    try:
        urllib.request.urlretrieve(URL, temporary)
        os.replace(temporary, download)
    finally:
        temporary.unlink(missing_ok=True)
    return download

def read_source(path):
    try:
        with path.open(newline="") as f:
            reader = csv.reader(f)
            metadata = dict(next(reader) for _ in range(5))
            header = next(reader)
        if not metadata.get("Version") or not metadata.get("Publication Date"):
            raise ValueError("Required Publication Date or Version metadata is missing")
        missing = set(REQUIRED_COLUMNS) - set(header)
        if missing: raise ValueError(f"Missing required columns: {sorted(missing)}")
        raw = pd.read_csv(path, skiprows=5, usecols=REQUIRED_COLUMNS, dtype=str,
                          keep_default_na=False, low_memory=False)
    except Exception as exc:
        raise ValueError(f"Cannot read regional CSV metadata/schema: {exc}") from exc
    return raw, dict(source_file=os.path.relpath(path, ROOT), publication_date=metadata["Publication Date"],
                     price_list_version=metadata["Version"], raw_row_count=len(raw),
                     raw_column_count=len(header), raw_size_bytes=path.stat().st_size)

def prepare(raw_path=None, refresh=False):
    output = ROOT / "data/processed"
    output.mkdir(parents=True, exist_ok=True)
    findings = {}
    try:
        path = resolve_source(raw_path, refresh)
        raw, metadata = read_source(path)
        findings["source"] = metadata
        components, filtering = filter_rates(raw, metadata)
        findings["filtering"] = filtering
        if not {"OnDemand","Reserved"} <= set(components.term_type):
            raise ValueError("Data availability: no comparable On-Demand or RI components remain.")
        prices, validation = pair_rates(components, filtering["anomalies"])
        findings["validation"] = validation
        if prices.empty: raise ValueError("Data availability: no valid RI options remain.")
        assert validation["candidate_ri_group_count"] == validation["accepted_group_count"] + validation["rejected_group_count"]
        with tempfile.TemporaryDirectory(prefix="ri-prepare-") as staging:
            stage = Path(staging)
            components.to_parquet(stage / "c6i_filtered_rate_components.parquet", index=False)
            prices.to_parquet(stage / "c6i_price_options.parquet", index=False)
            validation.update(metadata, retained_component_count=len(components),
                              retained_component_counts=filtering["retained_by_term"],
                              output_row_count=len(prices),
                              output_size_bytes=(stage / "c6i_price_options.parquet").stat().st_size)
            (stage / "filtering_report.json").write_text(json.dumps(filtering, indent=2))
            (stage / "validation_report.json").write_text(json.dumps(validation, indent=2))
            from src.load_data import load_price_options
            load_price_options(stage / "c6i_price_options.parquet")
            # Validate everything before publication. Roll back any interrupted write.
            backups = {p.name: (output / p.name).read_bytes() if (output / p.name).exists() else None
                       for p in stage.iterdir()}
            try:
                for p in stage.iterdir():
                    target = output / p.name
                    temp = output / (p.name + ".tmp")
                    temp.write_bytes(p.read_bytes())
                    os.replace(temp, target)
            except Exception:
                for name, content in backups.items():
                    if content is None: (output / name).unlink(missing_ok=True)
                    else:
                        temp = output / (name + ".tmp")
                        temp.write_bytes(content)
                        os.replace(temp, output / name)
                raise
        (output / "failed_report.json").unlink(missing_ok=True)
        print(f"Prepared {len(prices)} options from {len(raw):,} rows; {validation['rejected_group_count']} rejected groups.")
    except Exception as exc:
        atomic_json(output / "failed_report.json", dict(reason=str(exc), findings=findings))
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--raw-path", type=Path)
    group.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    try: prepare(args.raw_path, args.refresh)
    except Exception as exc: parser.exit(1, f"Preparation failed: {exc}\n")

if __name__ == "__main__":
    main()
