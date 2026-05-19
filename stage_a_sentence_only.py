"""
Post-Processing Stage A: sentence_only

- Populates SENT_TOKEN_START/END from DOC_TOKEN_START/END using
  doc_to_sent in token_lookup.yaml.
- Overwrites SENTENCE_ID with the value from token_lookup.
- Clears DOC_TOKEN_START/END.

Rows where DOC_TOKEN_START is blank, or where the lookup fails, are kept
with blank SENT_TOKEN_START/END (Stage B will try to recover them).

Input  : formatted/ordered/results_<run_id>_ordered.csv
Output : formatted/stage_a/results_<run_id>_a.csv
"""

import os
import argparse
import pandas as pd
import yaml


def load_token_lookup(path):
    with open(path) as f:
        return yaml.safe_load(f)


def doc_to_sent_pair(token_lookup, text_id, doc_id):
    if pd.isna(doc_id):
        return None, None
    try:
        doc_id_int = int(doc_id)
    except (TypeError, ValueError):
        return None, None
    text_map = token_lookup.get("doc_to_sent", {}).get(text_id)
    if text_map is None:
        return None, None
    entry = text_map.get(doc_id_int)
    if entry is None:
        return None, None
    return entry.get("sentence_id"), entry.get("token_id")


def process_file(input_path, output_path, token_lookup):
    df = pd.read_csv(input_path)

    sent_starts = []
    sent_ends = []
    sentence_ids = []

    for _, row in df.iterrows():
        text_id = row["TEXT_ID"]
        doc_start = row["DOC_TOKEN_START"]
        doc_end = row["DOC_TOKEN_END"]

        s_sent, s_tok = doc_to_sent_pair(token_lookup, text_id, doc_start)
        e_sent, e_tok = doc_to_sent_pair(token_lookup, text_id, doc_end)

        # Keep only if both endpoints map AND fall in the same sentence
        if s_sent is not None and e_sent is not None and s_sent == e_sent:
            sentence_ids.append(s_sent)
            sent_starts.append(s_tok)
            sent_ends.append(e_tok)
        else:
            # boundary cross or lookup failed → blank, Stage B will try to recover
            sentence_ids.append(pd.NA)
            sent_starts.append(pd.NA)
            sent_ends.append(pd.NA)

    df["SENTENCE_ID"] = sentence_ids
    df["SENT_TOKEN_START"] = sent_starts
    df["SENT_TOKEN_END"] = sent_ends

    # Discard doc-level IDs (sentence_only)
    df["DOC_TOKEN_START"] = pd.NA
    df["DOC_TOKEN_END"] = pd.NA

    int_cols = [
        "SENTENCE_ID",
        "ANNOTATION_ID",
        "SENT_TOKEN_START",
        "SENT_TOKEN_END",
        "DOC_TOKEN_START",
        "DOC_TOKEN_END",
    ]
    for col in int_cols:
        df[col] = df[col].astype("Int64")

    df.to_csv(output_path, index=False)
    return len(df), df["SENT_TOKEN_START"].notna().sum()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="formatted/ordered")
    parser.add_argument("--output_dir", default="formatted/stage_a")
    parser.add_argument("--token_lookup", default="token_lookup.yaml")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    token_lookup = load_token_lookup(args.token_lookup)

    files = sorted(
        f for f in os.listdir(args.input_dir)
        if f.endswith("_ordered.csv")
    )

    if not files:
        print(f"No _ordered.csv files found in {args.input_dir}")
        return

    print(f"Found {len(files)} _ordered.csv files")
    print(f"Output -> '{args.output_dir}/'")
    print("-" * 60)

    for fname in files:
        in_path = os.path.join(args.input_dir, fname)
        out_name = fname.replace("_ordered.csv", "_a.csv")
        out_path = os.path.join(args.output_dir, out_name)
        try:
            total, mapped = process_file(in_path, out_path, token_lookup)
            print(f"  {fname:55s} -> {out_name}  ({mapped}/{total} mapped)")
        except Exception as e:
            print(f"  {fname:55s} -> ERROR: {e}")

    print("-" * 60)
    print("Done.")


if __name__ == "__main__":
    main()