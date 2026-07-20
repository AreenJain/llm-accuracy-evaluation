"""
Stage E — drop the rows we couldn't fix.

The previous stages all use one convention: if they can't repair a
row, they blank its position columns. This is the cleanup step — it
just removes every such row. After E runs, the CSV has zero blanks
and is safe to feed to evaluate.py.

Like Stage D, this script exists as a CLI tool but the main use is
the importable `drop_unmatched(df)` helper called inline from
stage_a/b/c.
"""

import os
import argparse
import pandas as pd
import yaml


# Default data locations. The whole pipeline is run from the project root,
# so these relative paths resolve correctly. Loaded once and cached.
_DEFAULT_TEXT_DIR = "data/texts"
_DEFAULT_TOKEN_LOOKUP = "data/token_lookup.yaml"
_TEXT_CACHE = None
_LOOKUP_CACHE = None


def _load_story_tokens(text_dir=_DEFAULT_TEXT_DIR):
    """Return {text_id: [token, token, ...]} using the SAME whitespace split
    that the official scorer uses, so our checks match its checks exactly."""
    global _TEXT_CACHE
    if _TEXT_CACHE is None:
        _TEXT_CACHE = {}
        if os.path.isdir(text_dir):
            for fname in os.listdir(text_dir):
                if fname.endswith(".txt"):
                    tid = fname[:-len(".txt")]
                    with open(os.path.join(text_dir, fname), encoding="utf-8") as f:
                        _TEXT_CACHE[tid] = f.read().split()
    return _TEXT_CACHE


def _load_sent_to_doc(path=_DEFAULT_TOKEN_LOOKUP):
    """Return the sent_to_doc mapping from token_lookup.yaml (cached)."""
    global _LOOKUP_CACHE
    if _LOOKUP_CACHE is None:
        if os.path.exists(path):
            with open(path) as f:
                _LOOKUP_CACHE = yaml.safe_load(f).get("sent_to_doc", {})
        else:
            _LOOKUP_CACHE = {}
    return _LOOKUP_CACHE


def _row_matches_story(row, story_tokens, sent_to_doc):
    """Mirror evaluate.py's check_token_ids: the token text reported in the row
    must equal the story token(s) at its DOCUMENT position. We use the row's
    DOC_TOKEN_START if present, otherwise derive it from the sentence position
    via token_lookup (exactly as the scorer does). Returns True if it matches."""
    text_id = row["TEXT_ID"]
    tokens = str(row["TOKENS"]).split()
    if not tokens:
        return False

    raw = story_tokens.get(text_id)
    if raw is None:
        return False

    doc_start = row.get("DOC_TOKEN_START")
    if pd.isna(doc_start):
        # No doc id, derive it from the sentence position, like the scorer.
        try:
            doc_start = sent_to_doc[text_id][int(row["SENTENCE_ID"])][int(row["SENT_TOKEN_START"])]
        except (KeyError, TypeError, ValueError):
            return False
    doc_start = int(doc_start)

    for i, tok in enumerate(tokens):
        x = doc_start + i - 1          # submission ids are 1-based
        if x < 0 or x >= len(raw) or raw[x] != tok:
            return False
    return True


def drop_unmatched(df):
    """Return a copy of df ready for the scorer.

    Two clean-ups happen here (this is the "E" of the forced-convert tail):
      1. Drop rows we couldn't place at all (SENT_TOKEN_START is NaN).
      2. Drop rows whose reported tokens don't actually match the story at
         their position. These would otherwise crash evaluate.py with an
         AssertionError (e.g. the LLM wrote "11 point" but the story tokenises
         it as "11-point"). Only genuinely-broken rows are removed."""
    df = df[df["SENT_TOKEN_START"].notna()].copy()

    story_tokens = _load_story_tokens()
    sent_to_doc = _load_sent_to_doc()
    if story_tokens and len(df) > 0:
        keep = df.apply(lambda r: _row_matches_story(r, story_tokens, sent_to_doc), axis=1)
        df = df[keep].copy()

    int_cols = ["SENTENCE_ID", "ANNOTATION_ID", "SENT_TOKEN_START", "SENT_TOKEN_END",
                "DOC_TOKEN_START", "DOC_TOKEN_END"]
    for col in int_cols:
        df[col] = df[col].astype("Int64")
    return df


def process_file(input_path, output_path):
    """Standalone CLI helper."""
    df = pd.read_csv(input_path)
    total_before = len(df)
    df = drop_unmatched(df)
    total_after = len(df)
    df.to_csv(output_path, index=False)
    return total_before, total_after, total_before - total_after


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="results/formatted/stage_abcd")
    parser.add_argument("--output_dir", default="results/formatted/stage_abcde")
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
