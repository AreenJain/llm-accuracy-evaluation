"""
Stage B — nearest n-gram recovery.

After Stage A, some rows are still blank because the LLM's TOKENS span
either crossed two sentences or had no doc-id at all. This stage takes
those blank rows and tries to find the same word sequence somewhere
nearby in the story.

How it searches:
  1. If we know which sentence the mistake belongs to, scan that
     sentence first, starting from the original position and shifting
     outward symmetrically (0, +1, -1, +2, -2, ...). The TOKENS field
     tells us how many words to look for.
  2. If no match in that sentence — or no sentence id at all — scan the
     whole story sentence by sentence, left to right, until something
     matches exactly.

Rows that already had a valid position from Stage A are left alone.
Rows that still cannot be recovered stay blank for Stage C/D/E to clean up.

Same as Stage A, it saves two files:
  _ab.csv    — diagnostic, keeps blanks.
  _abde.csv  — D + E applied, ready for evaluate.py.

Input  : results/formatted/stage_a/results_<run_id>_a.csv
Output : results/formatted/stage_ab/results_<run_id>_ab.csv
         results/formatted/stage_abde/results_<run_id>_abde.csv
"""

import os
import re
import argparse
import pandas as pd

from stage_d_overlap_resolver import resolve_overlaps
from stage_e_drop_unmatched import drop_unmatched


def load_texts(text_dir):
    """Read every .txt story file and return a dict {text_id: full_text}."""
    texts = {}
    for fname in os.listdir(text_dir):
        if fname.endswith(".txt"):
            text_id = fname.replace(".txt", "")
            with open(os.path.join(text_dir, fname)) as f:
                texts[text_id] = f.read()
    return texts


def split_into_sentences(story):
    """Same sentence splitter the rest of the pipeline uses.
    Splits on '.', '!' or '?' followed by a space."""
    return re.split(r'(?<=[.!?]) +', story)


def get_sentence_tokens(story, sentence_id):
    """Return the word list of the 1-indexed sentence, or [] if out of range."""
    sentences = split_into_sentences(story)
    if sentence_id < 1 or sentence_id > len(sentences):
        return []
    return sentences[sentence_id - 1].split()


def search_n_gram(sentence_tokens, target_tokens, anchor_start=None):
    """Find target_tokens inside sentence_tokens. Returns (start, end) as
    1-indexed positions, or (None, None) if not found.

    If anchor_start is given, we try the original guess first and then
    spiral outward. If anchor_start is None, we just scan left to right.
    """
    n = len(target_tokens)
    max_start = len(sentence_tokens) - n + 1  # last position where a length-n span still fits
    if max_start < 1:
        return None, None

    # Build the list of starting positions to try, in priority order.
    if anchor_start is not None:
        anchor = anchor_start - 1  # convert to 0-indexed
        candidates = []
        max_dist = max(anchor, max_start - anchor)
        for d in range(max_dist + 1):
            if d == 0:
                if 0 <= anchor < max_start:
                    candidates.append(anchor)
            else:
                # offset +d first, then -d (so we get 0, +1, -1, +2, -2, ...)
                right = anchor + d
                if 0 <= right < max_start:
                    candidates.append(right)
                left = anchor - d
                if 0 <= left < max_start:
                    candidates.append(left)
    else:
        # No anchor — just walk through every possible position.
        candidates = list(range(max_start))

    # Try each starting position and return on the first exact match.
    for c in candidates:
        if sentence_tokens[c:c + n] == target_tokens:
            return c + 1, c + n  # convert back to 1-indexed
    return None, None


def process_file(input_path, output_ab_path, output_abde_path, texts):
    """Recover what we can for one _a.csv file."""
    df = pd.read_csv(input_path)

    recovered_in_sentence = 0
    recovered_via_doc_scan = 0

    for idx, row in df.iterrows():
        # If the row already has a position, skip it — nothing to recover.
        if pd.notna(row["SENT_TOKEN_START"]) and pd.notna(row["SENT_TOKEN_END"]):
            continue

        text_id = row["TEXT_ID"]
        sentence_id = row["SENTENCE_ID"]
        tokens_str = row["TOKENS"]

        # No TOKENS or unknown story — nothing to search for.
        if pd.isna(tokens_str) or text_id not in texts:
            continue
        target_tokens = str(tokens_str).split()
        if not target_tokens:
            continue

        # Step 1: try the sentence we already know about (if we do).
        if pd.notna(sentence_id):
            try:
                sid = int(sentence_id)
            except (TypeError, ValueError):
                sid = None
            if sid is not None:
                sentence_tokens = get_sentence_tokens(texts[text_id], sid)
                if sentence_tokens:
                    anchor = None
                    if pd.notna(row["SENT_TOKEN_START"]):
                        try:
                            anchor = int(row["SENT_TOKEN_START"])
                        except (TypeError, ValueError):
                            anchor = None
                    start, end = search_n_gram(sentence_tokens, target_tokens, anchor_start=anchor)
                    if start is not None:
                        df.at[idx, "SENT_TOKEN_START"] = start
                        df.at[idx, "SENT_TOKEN_END"] = end
                        recovered_in_sentence += 1
                        continue

        # Step 2: fall back to scanning the whole story sentence by sentence.
        sentences = split_into_sentences(texts[text_id])
        for s_idx, sent in enumerate(sentences, start=1):
            sentence_tokens = sent.split()
            start, end = search_n_gram(sentence_tokens, target_tokens, anchor_start=None)
            if start is not None:
                df.at[idx, "SENTENCE_ID"] = s_idx
                df.at[idx, "SENT_TOKEN_START"] = start
                df.at[idx, "SENT_TOKEN_END"] = end
                recovered_via_doc_scan += 1
                break

    # Cast int columns back to Int64 (recovery can introduce floats).
    int_cols = ["SENTENCE_ID", "ANNOTATION_ID", "SENT_TOKEN_START",
                "SENT_TOKEN_END", "DOC_TOKEN_START", "DOC_TOKEN_END"]
    for col in int_cols:
        df[col] = df[col].astype("Int64")

    # Diagnostic copy.
    df.to_csv(output_ab_path, index=False)

    # Evaluator-ready copy (apply D then E).
    df_de, _, _ = resolve_overlaps(df.copy())
    df_de = drop_unmatched(df_de)
    df_de.to_csv(output_abde_path, index=False)

    total = len(df)
    populated = df["SENT_TOKEN_START"].notna().sum()
    return total, populated, recovered_in_sentence, recovered_via_doc_scan, len(df_de)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="results/formatted/stage_a")
    parser.add_argument("--output_dir", default="results/formatted/stage_ab")
    parser.add_argument("--output_e_dir", default="results/formatted/stage_abde")
    parser.add_argument("--text_dir", default="data/texts")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.output_e_dir, exist_ok=True)
    texts = load_texts(args.text_dir)

    files = sorted(f for f in os.listdir(args.input_dir) if f.endswith("_a.csv"))
    if not files:
        print(f"No _a.csv files found in {args.input_dir}")
        return

    print(f"Found {len(files)} _a.csv files")
    print(f"Outputs -> '{args.output_dir}/' (full) and '{args.output_e_dir}/' (D+E)")
    print("-" * 70)

    for fname in files:
        in_path = os.path.join(args.input_dir, fname)
        out_ab = os.path.join(args.output_dir, fname.replace("_a.csv", "_ab.csv"))
        out_abde = os.path.join(args.output_e_dir, fname.replace("_a.csv", "_abde.csv"))
        try:
            total, populated, rec_sent, rec_doc, kept = process_file(in_path, out_ab, out_abde, texts)
            print(f"  {fname:55s} -> _ab ({populated}/{total}, +{rec_sent}/+{rec_doc}), _abde ({kept})")
        except Exception as e:
            print(f"  {fname:55s} -> ERROR: {e}")

    print("-" * 70)
    print("Done.")


if __name__ == "__main__":
    main()
