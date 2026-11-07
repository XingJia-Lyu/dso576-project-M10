"""Strict runtime handoff validation, independent of Streamlit."""
from pathlib import Path
from decimal import Decimal, InvalidOperation
import pandas as pd
from src.pair_rates import PRICE_COLUMNS
from src.filter_rates import PAYMENTS
from src.scenario import MONEY

class ProcessedDataError(ValueError):
    pass

def load_price_options(path: Path) -> pd.DataFrame:
    try:
        if not path.is_file(): raise ValueError(f"Processed file is missing: {path}")
        table = pd.read_parquet(path)
        missing = set(PRICE_COLUMNS) - set(table.columns)
        if missing: raise ValueError(f"Missing columns: {sorted(missing)}")
        if table.empty: raise ValueError("Price table is empty")
        if table[PRICE_COLUMNS].isna().any().any(): raise ValueError("Missing values")
        for field in ["price_list_version", "publication_date"]:
            if table[field].nunique() != 1 or not str(table[field].iloc[0]).strip():
                raise ValueError(f"Mixed or missing {field}")
        if not table.term_years.map(lambda x: not isinstance(x, bool) and x in (1,3) and int(x) == x).all():
            raise ValueError("Invalid term_years")
        if not table.purchase_option.isin(PAYMENTS).all(): raise ValueError("Invalid purchase option")
        if not table.offering_class.eq("standard").all(): raise ValueError("Invalid offering class")
        if not table.instance_type.map(lambda x: isinstance(x,str) and x.startswith("c6i.")).all():
            raise ValueError("Invalid instance type")
        if table.duplicated(["instance_type","term_years","purchase_option"]).any():
            raise ValueError("Duplicate option")
        for field in MONEY:
            for value in table[field]:
                if not isinstance(value,str): raise ValueError(f"{field} must be a decimal string")
                amount = Decimal(value)
                if not amount.is_finite() or amount < 0 or (field == "on_demand_hourly_usd" and amount <= 0):
                    raise ValueError(f"Invalid {field}")
        return table
    except Exception as exc:
        raise ProcessedDataError(
            f"Cannot load processed prices: {exc}. Run uv run python -m src.prepare_data"
        ) from exc
