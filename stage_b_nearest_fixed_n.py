"""
Post-Processing Stage B: nearest_fixed_n

For each row with blank SENT_TOKEN_START/END but a known SENTENCE_ID and TOKENS,
try to recover the span by searching within the sentence:
- Tokenize the sentence (same scheme as build_doc_token_map: split by whitespace)
- Tokenize the TOKENS field (whitespace split)
- Length of TOKENS = n
- Search at distances 0, +1, -1, +2, -2, ... from the original SENT_TOKEN_START
  (or scan all positions if SENT_TOKEN_START is also blank)
- If a same-length n-gram exactly matches, populate SENT_TOKEN_START/END

Rows that already have populated SENT_TOKEN_START/END are passed through unchanged.
Rows where no match is found remain blank (Stage C/D/E handle them).

Input  : formatted/stage_a/results_<run_id>_a.csv
Output : formatted/stage_b/results_<run_id>_ab.csv
"""

import os
import re
import argparse
import pandas as pd


def load_texts(text_dir):
    """Load all story texts into a dict {text_id: full_text}."""
    texts = {}
    for fname in os.listdir(text_dir):
        if fname.endswith(".txt"):
            text_id = fname.replace(".txt", "")
            with open(os.path.join(text_dir, fname)) as f:
                texts[text_id] = f.read()
    return texts


def split_into_sentences(story):
    """Same tokenization scheme as the pipeline's build_doc_token_map."""
    return re.split(r'(?<=[.!?]) +', story)


def get_sentence_tokens(story, sentence_id):
    """Return list of whitespace-split tokens for the given 1-indexed sentence."""
    sentences = split_into_sentences(story)
    if sentence_id < 1 or sentence_id > len(sentences):
        return []
    return sentences[sentence_id - 1].split()


def search_n_gram(sentence_tokens, target_tokens, anchor_start=None):
    """
    Search for target_tokens (list of strings) within sentence_tokens
    starting from anchor_start (1-indexed), shifting outward symmetrically.
    
    Returns (start, end) 1-indexed within sentence, or (None, None).
    """
    n = len(target_tokens)
    max_start = len(sentence_tokens) - n + 1  # 0-indexed last valid start
    if max_start < 1:
        return None, None
    
    # Build list of candidate starts (0-indexed) in distance order
    if anchor_start is not None:
        # anchor_start is 1-indexed → convert to 0-indexed
        anchor = anchor_start - 1
        candidates = []
        # offsets: 0, +1, -1, +2, -2, ...
        max_dist = max(anchor, max_start - anchor)
        for d in range(max_dist + 1):
            if d == 0:
                if 0 <= anchor < max_start:
                    candidates.append(anchor)
            else:
                # +d first
                right = anchor + d
                if 0 <= right < max_start:
                    candidates.append(right)
                # then -d
                left = anchor - d
                if 0 <= left < max_start:
                    candidates.append(left)
    else:
        # no anchor → scan left to right
        candidates = list(range(max_start))
    
    # Try each candidate
    for c in candidates:
        if sentence_tokens[c:c+n] == target_tokens:
            return c + 1, c + n  # 1-indexed
    return None, None


def process_file(input_path, output_path, texts):
    df = pd.read_csv(input_path)
    
    recovered_in_sentence = 0
    recovered_via_doc_scan = 0
    still_blank = 0
    
    for idx, row in df.iterrows():
        # If already populated, skip
        if pd.notna(row["SENT_TOKEN_START"]) and pd.notna(row["SENT_TOKEN_END"]):
            continue
        
        text_id = row["TEXT_ID"]
        sentence_id = row["SENTENCE_ID"]
        tokens_str = row["TOKENS"]
        
        if pd.isna(tokens_str) or text_id not in texts:
            still_blank += 1
            continue
        
        target_tokens = str(tokens_str).split()
        if not target_tokens:
            still_blank += 1
            continue
        
        # === CASE 1: SENTENCE_ID known → search within that sentence ===
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
        
        # === CASE 2: SENTENCE_ID blank or sentence search failed → scan whole document ===
        sentences = split_into_sentences(texts[text_id])
        found = False
        for s_idx, sent in enumerate(sentences, start=1):
            sentence_tokens = sent.split()
            start, end = search_n_gram(sentence_tokens, target_tokens, anchor_start=None)
            if start is not None:
                df.at[idx, "SENTENCE_ID"] = s_idx
                df.at[idx, "SENT_TOKEN_START"] = start
                df.at[idx, "SENT_TOKEN_END"] = end
                recovered_via_doc_scan += 1
                found = True
                break
        
        if not found:
            still_blank += 1
    
    # Re-cast int columns
    int_cols = ["SENTENCE_ID", "ANNOTATION_ID", "SENT_TOKEN_START", "SENT_TOKEN_END",
                "DOC_TOKEN_START", "DOC_TOKEN_END"]
    for col in int_cols:
        df[col] = df[col].astype("Int64")
    
    df.to_csv(output_path, index=False)
    total = len(df)
    populated = df["SENT_TOKEN_START"].notna().sum()
    return total, populated, recovered_in_sentence, recovered_via_doc_scan

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="formatted/stage_a")
    parser.add_argument("--output_dir", default="formatted/stage_b")
    parser.add_argument("--text_dir", default="texts")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    texts = load_texts(args.text_dir)
    
    files = sorted(f for f in os.listdir(args.input_dir) if f.endswith("_a.csv"))
    
    if not files:
        print(f"No _a.csv files found in {args.input_dir}")
        return
    
    print(f"Found {len(files)} _a.csv files")
    print(f"Output -> '{args.output_dir}/'")
    print("-" * 70)
    
    for fname in files:
        in_path = os.path.join(args.input_dir, fname)
        out_name = fname.replace("_a.csv", "_ab.csv")
        out_path = os.path.join(args.output_dir, out_name)
        try:
             total, populated, rec_sent, rec_doc = process_file(in_path, out_path, texts)
             print(f"  {fname:55s} -> {out_name}  ({populated}/{total} populated, +{rec_sent} in-sent, +{rec_doc} via doc-scan)")
        except Exception as e:
            print(f"  {fname:55s} -> ERROR: {e}")
    
    print("-" * 70)
    print("Done.")


if __name__ == "__main__":
    main()