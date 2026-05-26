"""
Format Converter (Phase 1)
Converts LLM CSVs to GSML column format.

Input  : results/llm_csv/results_<run_id>.csv
Output : results/formatted/ordered/results_<run_id>_ordered.csv
"""

import os
import argparse
import pandas as pd

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

INT_COLS = [
    "SENTENCE_ID",
    "ANNOTATION_ID",
    "SENT_TOKEN_START",
    "SENT_TOKEN_END",
    "DOC_TOKEN_START",
    "DOC_TOKEN_END",
]


def convert_file(input_path, output_path):
    df = pd.read_csv(input_path)

    for col in GSML_COLS:
        if col not in df.columns:
            df[col] = pd.NA

    for col in INT_COLS:
        if col in df.columns:
            df[col] = df[col].astype("Int64")
    
    # Normalize TYPE to uppercase (GSML expects uppercase categories)
    if "TYPE" in df.columns:
        df["TYPE"] = df["TYPE"].astype(str).str.upper().str.replace(" ", "_")

    df = df.loc[:, GSML_COLS]
    df.to_csv(output_path, index=False)
    return len(df)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="results/llm_csv")
    parser.add_argument("--output_dir", default="results/formatted/ordered")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

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