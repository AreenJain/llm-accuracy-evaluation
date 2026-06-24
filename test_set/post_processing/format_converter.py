"""
Stage 0 — Format Converter.

The LLM saves its annotations in a CSV that does not match the column
layout the official evaluator expects (the GSML format). This script
rearranges columns, fills in missing ones, makes sure integer fields
are stored as proper ints (not floats with .0 endings), and normalises
the TYPE column to uppercase.

Run it before any of the stage_a/b/c scripts.

Input  : results/llm_csv/results_<run_id>.csv
Output : results/formatted/ordered/results_<run_id>_ordered.csv
"""

import os
import argparse
import pandas as pd

# Columns the evaluator expects, in the exact order it expects them.
GSML_COLS = [
    "TEXT_ID",
    "SENTENCE_ID",
    "ANNOTATION_ID",
    "TOKENS",
    "SENT_TOKEN_START",
    "SENT_TOKEN_END",
    "DOC_TOKEN_START",
    "DOC_TOKEN_END",
    "TYPE",
    "CORRECTION",
    "COMMENT",
]

# Numeric columns that must stay as integers. We use pandas nullable Int64
# so blanks survive as NaN instead of being silently turned into floats.
INT_COLS = [
    "SENTENCE_ID",
    "ANNOTATION_ID",
    "SENT_TOKEN_START",
    "SENT_TOKEN_END",
    "DOC_TOKEN_START",
    "DOC_TOKEN_END",
]


def convert_file(input_path, output_path):
    """Read one LLM CSV, fix its layout, and write it back out."""
    df = pd.read_csv(input_path)

    # If the file has no rows (e.g., only metadata header), create
    # a sentinel row so downstream tools see an explicit "no
    # annotations" record instead of an entirely empty CSV.
    if df.shape[0] == 0:
        sentinel = {col: pd.NA for col in GSML_COLS}
        sentinel["TEXT_ID"] = "NO_ANNOTATIONS"
        sentinel["COMMENT"] = f"Source file: {os.path.basename(input_path)} (no annotations)"
        out_df = pd.DataFrame([sentinel])
        out_df.to_csv(output_path, index=False)
        return len(out_df)

    # If the LLM forgot any column, add it as empty so the schema still matches.
    for col in GSML_COLS:
        if col not in df.columns:
            df[col] = pd.NA

    # Force int columns to Int64. This is what stops "18" turning into "18.0".
    for col in INT_COLS:
        if col in df.columns:
            df[col] = df[col].astype("Int64")

    # GSML uses uppercase category names like "NUMBER", "NAME". The LLM
    # sometimes writes "Number" or "Name mistake" — fix that here.
    if "TYPE" in df.columns:
        df["TYPE"] = df["TYPE"].astype(str).str.upper().str.replace(" ", "_")

    # Drop any extra columns and write out in the canonical order.
    df = df.loc[:, GSML_COLS]
    df.to_csv(output_path, index=False)
    return len(df)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="results/llm_csv")
    parser.add_argument("--output_dir", default="results/formatted/ordered")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Pick up only raw LLM CSVs — skip anything that's already been processed.
    files = sorted(
        f for f in os.listdir(args.input_dir)
        if f.startswith("results_") and f.endswith(".csv")
        and not f.endswith("_cleaned.csv")
        and not f.endswith("_ordered.csv")
    )

    if not files:
        print(f"No matching CSVs found in {args.input_dir}")
        return

    print(f"Found {len(files)} files in '{args.input_dir}'")
    print(f"Output -> '{args.output_dir}/'")
    print("-" * 60)

    total_rows = 0
    for fname in files:
        in_path = os.path.join(args.input_dir, fname)
        out_name = fname.replace(".csv", "_ordered.csv")
        out_path = os.path.join(args.output_dir, out_name)
        try:
            n = convert_file(in_path, out_path)
            print(f"  {fname:50s} -> {out_name}  ({n} rows)")
            total_rows += n
        except Exception as e:
            print(f"  {fname:50s} -> ERROR: {e}")

    print("-" * 60)
    print(f"Done. Total rows: {total_rows}")


if __name__ == "__main__":
    main()
