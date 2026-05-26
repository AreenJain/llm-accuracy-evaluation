"""
Post-Processing Stage E: drop unmatched rows

Drops every row where SENT_TOKEN_START is blank.
After this stage, the CSV is fully populated and ready for evaluate.py.

Input  : formatted/stage_d/results_<run_id>_abcd.csv
Output : formatted/stage_e/results_<run_id>_abcde.csv
"""

import os
import argparse
import pandas as pd


def process_file(input_path, output_path):
    df = pd.read_csv(input_path)
    total_before = len(df)
    
    # Drop rows with blank SENT_TOKEN_START
    df = df[df["SENT_TOKEN_START"].notna()].copy()
    
    total_after = len(df)
    dropped = total_before - total_after
    
    # Recast int columns
    int_cols = ["SENTENCE_ID", "ANNOTATION_ID", "SENT_TOKEN_START", "SENT_TOKEN_END",
                "DOC_TOKEN_START", "DOC_TOKEN_END"]
    for col in int_cols:
        df[col] = df[col].astype("Int64")
    
    df.to_csv(output_path, index=False)
    return total_before, total_after, dropped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="formatted/stage_d")
    parser.add_argument("--output_dir", default="formatted/stage_e")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    files = sorted(f for f in os.listdir(args.input_dir) if f.endswith("_abcd.csv"))
    
    if not files:
        print(f"No _abcd.csv files found in {args.input_dir}")
        return
    
    print(f"Found {len(files)} _abcd.csv files")
    print(f"Output -> '{args.output_dir}/'")
    print("-" * 70)
    
    for fname in files:
        in_path = os.path.join(args.input_dir, fname)
        out_name = fname.replace("_abcd.csv", "_abcde.csv")
        out_path = os.path.join(args.output_dir, out_name)
        try:
            before, after, dropped = process_file(in_path, out_path)
            print(f"  {fname:55s} -> {out_name}  ({after} kept, {dropped} dropped from {before})")
        except Exception as e:
            print(f"  {fname:55s} -> ERROR: {e}")
    
    print("-" * 70)
    print("Done.")


if __name__ == "__main__":
    main()