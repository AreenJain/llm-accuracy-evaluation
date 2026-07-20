"""
Stage D — overlap resolver (greedy, left-to-right).

The LLM sometimes flags the same chunk of text more than once: two
annotations covering the same tokens, or overlapping spans. The
evaluator refuses to run when that happens — it errors out with
"Token X already used, duplicate".

This stage walks through every story's annotations from left to right
(by sentence id, then by start position) and keeps the first one to
claim each token. Any later annotation that touches an already-used
token gets its position fields blanked, so Stage E can drop it.

Stage A, B, and C all import `resolve_overlaps` from here and apply it
inline, which is why this script is rarely run on its own. The CLI is
kept for diagnostic / one-off use.
"""

import os
import argparse
import pandas as pd


def resolve_overlaps(df):
    """Remove overlapping spans in a DataFrame. Modifies in place and also
    returns (df, kept_count, blanked_count) for logging.

    Algorithm:
      1. Find every row with a populated SENT_TOKEN_START.
      2. Sort by (TEXT_ID, SENTENCE_ID, SENT_TOKEN_START) so we walk
         left-to-right within each story.
      3. Keep a set of (sentence_id, token_id) pairs already taken by
         a kept row. If a new row's tokens overlap that set, blank it.
    """
    kept = 0
    blanked_overlap = 0
    used_per_doc = {}

    populated_idx = df[df["SENT_TOKEN_START"].notna()].index.tolist()

    # Build (text_id, sentence_id, start, row_index) tuples for stable sort.
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

        # First time we see this story give it a fresh set of used tokens.
        if text_id not in used_per_doc:
            used_per_doc[text_id] = set()

        # The full token coverage of this annotation, as (sentence_id, token_id) pairs.
        span_tokens = {(sent_id, t) for t in range(start, end + 1)}

        if span_tokens & used_per_doc[text_id]:
            # Conflict an earlier (kept) row already owns one of these tokens.
            df.at[idx, "SENT_TOKEN_START"] = pd.NA
            df.at[idx, "SENT_TOKEN_END"] = pd.NA
            df.at[idx, "SENTENCE_ID"] = pd.NA
            blanked_overlap += 1
        else:
            # No conflict claim these tokens.
            used_per_doc[text_id].update(span_tokens)
            kept += 1

    # Recast int columns so blanks stay as proper NaN (not floats).
    int_cols = ["SENTENCE_ID", "ANNOTATION_ID", "SENT_TOKEN_START", "SENT_TOKEN_END",
                "DOC_TOKEN_START", "DOC_TOKEN_END"]
    for col in int_cols:
        df[col] = df[col].astype("Int64")

    return df, kept, blanked_overlap


def process_file(input_path, output_path):
    """Standalone CLI helper — read one file, apply resolve_overlaps, write it."""
    df = pd.read_csv(input_path)
    df, kept, blanked_overlap = resolve_overlaps(df)
    df.to_csv(output_path, index=False)
    total = len(df)
    populated = df["SENT_TOKEN_START"].notna().sum()
    return total, populated, kept, blanked_overlap


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="results/formatted/stage_abc")
    parser.add_argument("--output_dir", default="results/formatted/stage_abcd")
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
