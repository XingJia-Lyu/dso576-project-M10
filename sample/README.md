# How these samples were drawn

Eleven small CSV files cut from the full AWS price-list downloads, so that you can write and test code
before the real files arrive. Section 4 of `data_overview_aws-price-list.md` explains how to download the
full files, and section 5 is the column dictionary.

Every sample file is a plain UTF-8 CSV with a comma delimiter, a header row, and **all columns of the source
table**. No column was dropped or truncated.

## What changed between the full file and the sample

One thing only: the five metadata lines that sit above the header in every full price-list file were removed,
so line 1 of a sample is the header and `pd.read_csv(path)` opens it with no extra arguments. Those five
lines carry the format version, the disclaimer, the publication date, the version stamp and the offer code.
Section 4 of the data overview document shows how to read them from a full file.

Nothing else was altered. Values are exactly as published: `PricePerUnit` still reads `0.1920000000`,
`EndingRange` still holds the literal string `Inf`, `Memory` still reads `16 GiB`, and `NA`, `N/A` and empty
strings are all preserved as they appear in the full files.

## The files

| Sample file | Full file it came from | Rows in the full file | Rows in the sample | Columns | Size | Method |
|---|---|---|---|---|---|---|
| `ec2_us-east-1_sample.csv` | `ec2_us-east-1.csv` | 394,515 | 4,000 | 93 | 2.68 MB | uniform random, DuckDB reservoir sample, seed 576 |
| `ec2_eu-west-1_sample.csv` | `ec2_eu-west-1.csv` | 369,916 | 4,000 | 93 | 2.65 MB | uniform random, DuckDB reservoir sample, seed 576 |
| `rds_us-east-1_sample.csv` | `rds_us-east-1.csv` | 30,485 | 5,000 | 58 | 2.60 MB | uniform random, DuckDB reservoir sample, seed 576 |
| `sagemaker_all_sample.csv` | `sagemaker_all.csv` | 40,654 | 5,000 | 67 | 2.52 MB | uniform random, DuckDB reservoir sample, seed 576 |
| `s3_all_sample.csv` | `s3_all.csv` | 9,943 | 9,943 | 35 | 3.87 MB | whole table |
| `lambda_all_sample.csv` | `lambda_all.csv` | 10,620 | 10,620 | 24 | 3.95 MB | whole table |
| `bedrock_foundation_models_sample.csv` | `bedrock_foundation_models.csv` | 5,669 | 5,669 | 17 | 1.90 MB | whole table |
| `bedrock_service_all_sample.csv` | `bedrock_service_all.csv` | 11,657 | 11,657 | 35 | 4.82 MB | whole table |
| `ec2_us-east-1_history_sample.csv` | eight archived EC2 us-east-1 versions | 1,628,775 | 6,400 | 94 | 4.22 MB | 800 rows per version, DuckDB reservoir sample, seed 576, stacked |
| `aws_offer_index.csv` | `offer_index.json` | 269 | 269 | 6 | 0.05 MB | whole file, flattened |
| `ec2_version_index.csv` | `ec2_version_index.json` | 122 | 122 | 4 | 0.01 MB | whole file, flattened |

Total: eleven files, 29 MB.

## Reproducing the samples yourself

The random samples were drawn with DuckDB's `USING SAMPLE n ROWS (reservoir, 576)`, which is uniform random
selection without replacement, with 576 as the random seed. Running the same statement against the same full
file with the same DuckDB version reproduces a sample exactly.

DuckDB is a small database engine that reads CSV files directly, and it is not installed by default. You do
not need to install anything permanently: run your script with

```
uv run --with duckdb --with pandas python your_script.py
```

and uv fetches DuckDB for that one run. Inside the script, the statement that cut
`ec2_us-east-1_sample.csv` from the full file was, in effect, a `SELECT *` over
`read_csv('data/ec2_us-east-1.csv', skip=5, header=true, all_varchar=true)` with
`USING SAMPLE 4000 ROWS (reservoir, 576)` on the end. `skip=5` steps over the five metadata lines,
`header=true` takes line 6 as the column names, and `all_varchar=true` reads every column as text so that
nothing is silently converted.

## Two files that need explaining

**`ec2_us-east-1_history_sample.csv`** stacks eight archived versions of the EC2 us-east-1 price list into
one table, 800 randomly chosen rows from each. Those eight versions do not have the same columns: the 2018
file has 77, the 2025 file has 91, and the 2018 file has a column (`Elastic GPU Type`) that later files
dropped. The stack was made with an operation that unions on column name and leaves a cell empty where a
version did not have that column, so **every column that appears in any of the eight versions appears in this
file** and nothing is lost. Two columns were added at the front so you can tell the versions apart:

- `source_file`, the name of the archived file, for example `ec2_us-east-1_20180910235641.csv`
- `price_list_version`, the 14-digit version stamp, for example `20180910235641`

Between them the eight versions use 92 distinct column names, and those two were added in front, which is
why this file has 94 columns rather than the 91 of the 2025 file. Every other sample has exactly the columns
of its source.

Empty cells in this file therefore mean two different things: either the value was empty in that version's
file, or that version had no such column at all. The column-by-version table in section 5 of
`data_overview_aws-price-list.md` says which is which.

**`aws_offer_index.csv` and `ec2_version_index.csv`** are the two index files turned into tables. The raw
JSON is an object keyed by offer code or by version stamp; each key became one row and the key itself became
the first column (`offerCode`, `version`). No values were changed. These are complete, not samples: all 269
offers and all 122 EC2 versions are here. `ec2_version_index.csv` is the file to read if you want to reach
back in time, because it gives every version stamp with the dates it was in force, and the stamp is what goes
into the download address. Section 4 of the data overview document shows how.

## Reading a sample

`pd.read_csv(path)` opens all eleven files with no parse errors and no dtype warnings. Pass `dtype=str` and
`keep_default_na=False` if you want the raw strings preserved exactly, which matters because `EndingRange`
contains the literal `Inf`, several columns contain the literal string `NA` that pandas would otherwise treat
as missing, and `PricePerUnit` is a fixed-decimal string such as `0.1920000000`.

## The caveat that matters

These are **a sample; counts and proportions here are not population figures**. The four largest tables hold
a random subset of rows, so a count of GPU instances, a share of reserved rows, or an average price taken
from `ec2_us-east-1_sample.csv` is not the real figure for the region. Recompute anything you intend to
report against the full download.

Two traps specific to sampling this dataset:

1. **The samples break the reserved-instance pairing.** A reserved term is two rows, an upfront-fee row and
   an hourly row, and a random sample will almost always take one without the other. Effective hourly rates
   cannot be computed from these files. Do that against the full download.
2. **A sampled EC2 file will usually not contain the row you want.** Only about 1,251 of the 394,515 rows in
   the full file are plain on-demand Linux shared-tenancy compute rows, so a 4,000-row sample holds roughly a
   dozen of them and may hold none for any particular instance type. The samples are for seeing what the
   columns look like and testing parsing code. Every number goes back to the full download.

The four whole-table files (`s3_all`, `lambda_all`, and both Bedrock files) can be counted directly, but they
are complete only as of the publication dates listed in section 4 of the data overview document.
