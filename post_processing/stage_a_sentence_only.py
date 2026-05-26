"""
Stage A — sentence-only mapping.

The LLM gives us each mistake's position as a document-level token id
(DOC_TOKEN_START / DOC_TOKEN_END). The evaluator, on the other hand,
wants the position relative to a single sentence (SENT_TOKEN_START /
SENT_TOKEN_END), along with the sentence id.

This stage uses the prebuilt mapping in data/token_lookup.yaml to
translate doc-level ids into (sentence_id, sent_token_id). If the
mistake span crosses two sentences, we blank that row — Stage B will
try to recover it later.

It writes two files for every input:

  _a.csv    — every row preserved, including blank ones (diagnostic).
  _ade.csv  — same data but with Stage D (overlap removal) and Stage E
              (drop unmatched) applied on top, so it is ready for
              evaluate.py.

Input  : results/formatted/ordered/results_<run_id>_ordered.csv
Output : results/formatted/stage_a/results_<run_id>_a.csv
         results/formatted/stage_ade/results_<run_id>_ade.csv
"""

import os
import argparse
import pandas as pd
import yaml

# D and E are tiny helpers in their own files; we reuse them here so
# Stage A can emit an "evaluator-ready" version directly.
from stage_d_overlap_resolver import resolve_overlaps
from stage_e_drop_unmatched import drop_unmatched


def load_token_lookup(path):
    """Load the doc-id -> (sentence_id, token_id) map from YAML."""
    with open(path) as f:
        return yaml.safe_load(f)


def doc_to_sent_pair(token_lookup, text_id, doc_id):
    """Look up one doc-token id. Returns (sentence_id, token_id) or (None, None)
    if the id is missing, not an integer, or the story isn't in the lookup."""
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


def process_file(input_path, output_a_path, output_ade_path, token_lookup):
    """Convert one _ordered.csv into its _a.csv and _ade.csv siblings."""
    df = pd.read_csv(input_path)

    sent_starts = []
    sent_ends = []
    sentence_ids = []

    # Walk row by row. For each annotation, translate the start and end
    # doc-ids into sentence-level ids. Both ends must live in the same
    # sentence for us to accept the row — otherwise the span is unusable.
    for _, row in df.iterrows():
        text_id = row["TEXT_ID"]
        doc_start = row["DOC_TOKEN_START"]
        doc_end = row["DOC_TOKEN_END"]

        s_sent, s_tok = doc_to_sent_pair(token_lookup, text_id, doc_start)
        e_sent, e_tok = doc_to_sent_pair(token_lookup, text_id, doc_end)

        if s_sent is not None and e_sent is not None and s_sent == e_sent:
            sentence_ids.append(s_sent)
            sent_starts.append(s_tok)
            sent_ends.append(e_tok)
        else:
            # Cross-sentence span or lookup failure — leave blank for Stage B.
            sentence_ids.append(pd.NA)
            sent_starts.append(pd.NA)
            sent_ends.append(pd.NA)

    # Write the new sentence-level columns back and clear the doc-level ones.
    df["SENTENCE_ID"] = sentence_ids
    df["SENT_TOKEN_START"] = sent_starts
    df["SENT_TOKEN_END"] = sent_ends
    df["DOC_TOKEN_START"] = pd.NA
    df["DOC_TOKEN_END"] = pd.NA

    # Keep integer columns as Int64 so blanks stay blank (no "18.0" mess).
    int_cols = ["SENTENCE_ID", "ANNOTATION_ID", "SENT_TOKEN_START",
                "SENT_TOKEN_END", "DOC_TOKEN_START", "DOC_TOKEN_END"]
    for col in int_cols:
        df[col] = df[col].astype("Int64")

    # Diagnostic copy — keeps every row, even the unmapped ones.
    df.to_csv(output_a_path, index=False)

    # Evaluator-ready copy — apply D and E, then save.
    df_de, _, _ = resolve_overlaps(df.copy())
    df_de = drop_unmatched(df_de)
    df_de.to_csv(output_ade_path, index=False)

    total = len(df)
    mapped = df["SENT_TOKEN_START"].notna().sum()
    return total, mapped, len(df_de)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="results/formatted/ordered")
    parser.add_argument("--output_dir", default="results/formatted/stage_a")
    parser.add_argument("--output_e_dir", default="results/formatted/stage_ade")
    parser.add_argument("--token_lookup", default="data/token_lookup.yaml")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.output_e_dir, exist_ok=True)
    token_lookup = load_token_lookup(args.token_lookup)

    files = sorted(f for f in os.listdir(args.input_dir) if f.endswith("_ordered.csv"))
    if not files:
        print(f"No _ordered.csv files found in {args.input_dir}")
        return

    print(f"Found {len(files)} _ordered.csv files")
    print(f"Outputs -> '{args.output_dir}/' (full) and '{args.output_e_dir}/' (D+E)")
    print("-" * 70)

    for fname in files:
        in_path = os.path.join(args.input_dir, fname)
        out_a = os.path.join(args.output_dir, fname.replace("_ordered.csv", "_a.csv"))
        out_ade = os.path.join(args.output_e_dir, fname.replace("_ordered.csv", "_ade.csv"))
        try:
            total, mapped, kept = process_file(in_path, out_a, out_ade, token_lookup)
            print(f"  {fname:55s} -> _a ({mapped}/{total}), _ade ({kept} kept)")
        except Exception as e:
            print(f"  {fname:55s} -> ERROR: {e}")

    print("-" * 70)
    print("Done.")


if __name__ == "__main__":
    main()
