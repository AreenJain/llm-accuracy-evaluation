"""
Post-Processing Stage D: greedy_left_to_right overlap resolver

For each document (TEXT_ID), look at all rows with populated spans.
Sort by SENT_TOKEN_START. Keep the first row, then for each subsequent
row check if any of its tokens overlap with already-used tokens. If yes,
blank out that row (SENT_TOKEN_START / SENT_TOKEN_END / SENTENCE_ID).

Overlap is checked at the sentence level: a span belongs to (TEXT_ID,
SENTENCE_ID) and we track used (sentence_id, token_id) pairs per document.

Rows that were already blank pass through unchanged.

Input  : formatted/stage_abc/results_<run_id>_abc.csv
Output : formatted/stage_abcd/results_<run_id>_abcd.csv
"""

import os
import argparse
import pandas as pd


def resolve_overlaps(df):
    """In-place greedy left-to-right overlap removal. Returns (df, kept, blanked)."""
    kept = 0
    blanked_overlap = 0
    used_per_doc = {}
    
    # Process in row order but sort populated rows by (TEXT_ID, SENTENCE_ID, SENT_TOKEN_START)
    # so greedy left to right works deterministically.
    populated_idx = df[df["SENT_TOKEN_START"].notna()].index.tolist()
    
    # Build sortable tuples then sort
    sortable = []
    for i in populated_idx:
        row = df.loc[i]
        sortable.append((
            str(row["TEXT_ID"]),
            int(row["SENTENCE_ID"]) if pd.notna(row["SENTENCE_ID"]) else 0,
            int(row["SENT_TOKEN_START"]),
            i,
        ))
    sortable.sort()
    
    for text_id, sent_id, start, idx in sortable:
        end = int(df.at[idx, "SENT_TOKEN_END"])
        
        if text_id not in used_per_doc:
            used_per_doc[text_id] = set()
        
        span_tokens = {(sent_id, t) for t in range(start, end + 1)}
        
        if span_tokens & used_per_doc[text_id]:
            # Overlap then blank this row
            df.at[idx, "SENT_TOKEN_START"] = pd.NA
            df.at[idx, "SENT_TOKEN_END"] = pd.NA
            df.at[idx, "SENTENCE_ID"] = pd.NA
            blanked_overlap += 1
        else:
            used_per_doc[text_id].update(span_tokens)
            kept += 1
    
    int_cols = ["SENTENCE_ID", "ANNOTATION_ID", "SENT_TOKEN_START", "SENT_TOKEN_END",
                "DOC_TOKEN_START", "DOC_TOKEN_END"]
    for col in int_cols:
        df[col] = df[col].astype("Int64")

    return df, kept, blanked_overlap


def process_file(input_path, output_path):
    df = pd.read_csv(input_path)
    df, kept, blanked_overlap = resolve_overlaps(df)
    df.to_csv(output_path, index=False)
    total = len(df)
    populated = df["SENT_TOKEN_START"].notna().sum()
    return total, populated, kept, blanked_overlap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="formatted/stage_abc")
    parser.add_argument("--output_dir", default="formatted/stage_abcd")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    files = sorted(f for f in os.listdir(args.input_dir) if f.endswith("_abc.csv"))
    
    if not files:
        print(f"No _abc.csv files found in {args.input_dir}")
        return
    
    print(f"Found {len(files)} _abc.csv files")
    print(f"Output -> '{args.output_dir}/'")
    print("-" * 70)
    
    for fname in files:
        in_path = os.path.join(args.input_dir, fname)
        out_name = fname.replace("_abc.csv", "_abcd.csv")
        out_path = os.path.join(args.output_dir, out_name)
        try:
            total, populated, kept, blanked = process_file(in_path, out_path)
            print(f"  {fname:55s} -> {out_name}  ({populated}/{total} populated, kept={kept}, overlap_blanked={blanked})")
        except Exception as e:
            print(f"  {fname:55s} -> ERROR: {e}")
    
    print("-" * 70)
    print("Done.")


if __name__ == "__main__":
    main()