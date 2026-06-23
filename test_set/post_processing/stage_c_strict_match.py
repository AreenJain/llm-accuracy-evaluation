"""
Stage C — strict-match validation.

By now every populated row claims a SENTENCE_ID and a span within that
sentence. But the LLM (or Stage B's search) might still have written
down a position that doesn't actually point at the words it says it
does. This stage double-checks.

For every row that has a position:
  - Pull the actual words sitting at that position in the story.
  - Compare them word-for-word against the TOKENS field.
  - If they match exactly: keep the row.
  - If anything is off (mismatch, out-of-range index, non-integer id):
    blank the position fields so the row gets dropped later.

Rows that were already blank are passed through untouched.

Saves two files like the previous stages:
  _abc.csv    — diagnostic, keeps blanks.
  _abcde.csv  — D + E applied, ready for evaluate.py (this is the
                final, fully cleaned output of the whole pipeline).

Input  : results/formatted/stage_ab/results_<run_id>_ab.csv
Output : results/formatted/stage_abc/results_<run_id>_abc.csv
         results/formatted/stage_abcde/results_<run_id>_abcde.csv
"""

import os
import re
import argparse
import pandas as pd

from stage_d_overlap_resolver import resolve_overlaps
from stage_e_drop_unmatched import drop_unmatched


def load_texts(text_dir):
    """Read every story .txt into a dict {text_id: full_text}."""
    texts = {}
    for fname in os.listdir(text_dir):
        if fname.endswith(".txt"):
            text_id = fname.replace(".txt", "")
            with open(os.path.join(text_dir, fname)) as f:
                texts[text_id] = f.read()
    return texts


def split_into_sentences(story):
    """Same sentence splitter used everywhere else."""
    return re.split(r'(?<=[.!?]) +', story)


def get_sentence_tokens(story, sentence_id):
    """Word list of the 1-indexed sentence."""
    sentences = split_into_sentences(story)
    if sentence_id < 1 or sentence_id > len(sentences):
        return []
    return sentences[sentence_id - 1].split()


def process_file(input_path, output_abc_path, output_abcde_path, texts):
    """Validate one _ab.csv and produce both stage_abc and stage_abcde outputs."""
    df = pd.read_csv(input_path)

    kept = 0
    blanked = 0

    for idx, row in df.iterrows():
        # Skip rows that are already blank — Stage B already gave up on them.
        if pd.isna(row["SENT_TOKEN_START"]) or pd.isna(row["SENT_TOKEN_END"]):
            continue

        text_id = row["TEXT_ID"]
        sentence_id = row["SENTENCE_ID"]
        tokens_str = row["TOKENS"]

        # Sanity check: must know which story, which sentence, and what tokens.
        if text_id not in texts or pd.isna(sentence_id) or pd.isna(tokens_str):
            df.at[idx, "SENT_TOKEN_START"] = pd.NA
            df.at[idx, "SENT_TOKEN_END"] = pd.NA
            df.at[idx, "SENTENCE_ID"] = pd.NA
            blanked += 1
            continue

        # Cast ids to int. If any of them is garbage, blank the row.
        try:
            sid = int(sentence_id)
            start = int(row["SENT_TOKEN_START"])
            end = int(row["SENT_TOKEN_END"])
        except (TypeError, ValueError):
            df.at[idx, "SENT_TOKEN_START"] = pd.NA
            df.at[idx, "SENT_TOKEN_END"] = pd.NA
            df.at[idx, "SENTENCE_ID"] = pd.NA
            blanked += 1
            continue

        # Pull the actual word list from the story at the claimed position.
        sentence_tokens = get_sentence_tokens(texts[text_id], sid)
        target_tokens = str(tokens_str).split()

        # Bounds check.
        if start < 1 or end > len(sentence_tokens) or start > end:
            df.at[idx, "SENT_TOKEN_START"] = pd.NA
            df.at[idx, "SENT_TOKEN_END"] = pd.NA
            df.at[idx, "SENTENCE_ID"] = pd.NA
            blanked += 1
            continue

        # Final word-for-word check.
        actual = sentence_tokens[start - 1:end]
        if actual == target_tokens:
            kept += 1
        else:
            df.at[idx, "SENT_TOKEN_START"] = pd.NA
            df.at[idx, "SENT_TOKEN_END"] = pd.NA
            df.at[idx, "SENTENCE_ID"] = pd.NA
            blanked += 1

    int_cols = ["SENTENCE_ID", "ANNOTATION_ID", "SENT_TOKEN_START",
                "SENT_TOKEN_END", "DOC_TOKEN_START", "DOC_TOKEN_END"]
    for col in int_cols:
        df[col] = df[col].astype("Int64")

    # Diagnostic copy.
    df.to_csv(output_abc_path, index=False)

    # Evaluator-ready copy — final stage output.
    df_de, _, _ = resolve_overlaps(df.copy())
    df_de = drop_unmatched(df_de)
    df_de.to_csv(output_abcde_path, index=False)

    total = len(df)
    populated = df["SENT_TOKEN_START"].notna().sum()
    return total, populated, kept, blanked, len(df_de)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="test_set/results/formatted/stage_ab")
    parser.add_argument("--output_dir", default="test_set/results/formatted/stage_abc")
    parser.add_argument("--output_e_dir", default="test_set/results/formatted/stage_abcde")
    parser.add_argument("--text_dir", default="test_set/data/texts")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.output_e_dir, exist_ok=True)
    texts = load_texts(args.text_dir)

    files = sorted(f for f in os.listdir(args.input_dir) if f.endswith("_ab.csv"))
    if not files:
        print(f"No _ab.csv files found in {args.input_dir}")
        return

    print(f"Found {len(files)} _ab.csv files")
    print(f"Outputs -> '{args.output_dir}/' (full) and '{args.output_e_dir}/' (D+E)")
    print("-" * 70)

    for fname in files:
        in_path = os.path.join(args.input_dir, fname)
        out_abc = os.path.join(args.output_dir, fname.replace("_ab.csv", "_abc.csv"))
        out_abcde = os.path.join(args.output_e_dir, fname.replace("_ab.csv", "_abcde.csv"))
        try:
            total, populated, kept, blanked, e_kept = process_file(in_path, out_abc, out_abcde, texts)
            print(f"  {fname:55s} -> _abc ({populated}/{total}, kept={kept}), _abcde ({e_kept})")
        except Exception as e:
            print(f"  {fname:55s} -> ERROR: {e}")

    print("-" * 70)
    print("Done.")


if __name__ == "__main__":
    main()
