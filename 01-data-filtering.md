# 01 - Data filtering contract

## Purpose

This file is the handoff from the raw AWS price sheet to the formula work. It produces only comparable C6i rate components; it does not pair RI charges, calculate costs, or build any user interface. The source of truth is the **full** regional EC2 file at `data/ec2_us-east-1.csv`. The random sample is useful for parsing tests only and must never produce a displayed cost or savings figure.

## Inputs

Read the first five CSV rows separately as metadata and preserve `Publication Date` and `Version`. Read the data rows with:

```python
pd.read_csv(path, skiprows=5, dtype=str, keep_default_na=False, low_memory=False)
```

Keep the price amount as a decimal string until the formula layer converts it to `Decimal`. `NA` is a real value in the source and must not become a null.

## Comparable-rate filter

Keep rows satisfying every common product condition below:

```text
Product Family     = Compute Instance
Region Code        = us-east-1
Operating System   = Linux
Tenancy            = Shared
CapacityStatus     = Used
Pre Installed S/W  = NA
Instance Type      starts with c6i.
Currency           = USD
```

`Product Family = Compute Instance` intentionally excludes `c6i.metal`, which is classified as bare metal. The first release must state this boundary rather than silently mixing product families.

Then retain only these purchasable rate components:

- On-Demand: `TermType = OnDemand` and `Unit = Hrs`.
- Standard RI: `TermType = Reserved`, `OfferingClass = standard`, `LeaseContractLength` normalized to `1yr` or `3yr`, and `Unit` equal to `Hrs` or `Quantity`.

Normalize `1 yr` to `1yr`, `3 yr` to `3yr`, and remove the optional spaces in `All Upfront`, `Partial Upfront`, and `No Upfront` before assigning the canonical labels. Do not retain convertible RIs.

## Output contract

Write `data/processed/c6i_filtered_rate_components.parquet`. Each row remains one AWS rate component and contains:

| Column | Meaning |
| --- | --- |
| `price_list_version`, `publication_date` | Source identity from the five metadata rows |
| `sku`, `offer_term_code` | AWS keys used later to pair RI components |
| `instance_type` | Selected C6i type, such as `c6i.xlarge` |
| `term_type` | `OnDemand` or `Reserved` |
| `term_years` | `null`, `1`, or `3` |
| `purchase_option` | `OnDemand`, `No Upfront`, `Partial Upfront`, or `All Upfront` |
| `offering_class` | `null` for On-Demand or `standard` for RIs |
| `unit` | `Hrs` or `Quantity` |
| `price_per_unit_usd` | Exact decimal string from `PricePerUnit` |

Write a small validation report beside it with source version, input row count, retained row count, retained instance types, and every excluded or ambiguous rate key. The report is evidence for the formula team; it is not a user-facing result.

## Required validations

- Each retained On-Demand rate must have a non-negative `Hrs` price.
- A retained RI key is identified by `sku + offer_term_code`; the filter does not combine it yet.
- No `Unit` other than `Hrs` or `Quantity` may enter the processed file.
- Every RI has a canonical one- or three-year term, a canonical payment option, and `standard` offering class.
- The output has at least one comparable On-Demand rate and one RI component before downstream work begins. Otherwise fail with a clear data-availability message.

## Three-person data-work split

1. **Reader and metadata owner:** parse the full file, retain the version metadata, and preserve source strings exactly.
2. **Filter and normalizer owner:** apply the common filters and standardize term/payment labels.
3. **Validation owner:** verify counts, keys, allowed values, and write the validation report; test that the random sample is rejected for final calculations.
