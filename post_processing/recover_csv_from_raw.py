"""
Rebuild a results CSV from its raw JSONL.

Some runs produced a valid raw JSONL but an empty CSV. This happens when
grove_pipeline's strict Pydantic parser rejects the model's output — e.g.
the p4 prompt returns TOKENS + LEFT/RIGHT_CONTEXT but no ANNOTATION_ID, or
a model returned a bare JSON object instead of a list. The raw text is still
saved, so we can re-parse it here with a forgiving json.loads and rebuild the
CSV without re-running the model.

The output columns and the DOC_TOKEN_START/END computation match exactly what
grove_pipeline writes, so the recovered CSV drops straight into the normal
post-processing pipeline.

Usage:
    python3 post_processing/recover_csv_from_raw.py \
        --raw   results/llm_raw/raw_outputs_qwen_medium_p4_run1.jsonl \
        --games data/games_30_rows.csv \
        --out   results/llm_csv/results_qwen_medium_p4_run1.csv \
        --model qwen_medium --prompt_key p4
"""

import os
import re
import json
import argparse
import pandas as pd


def build_doc_token_map(story):
    """Same tokenisation grove_pipeline uses: split into sentences on
    sentence-final punctuation, then split each sentence on whitespace.
    Returns {doc_token_id (1-indexed): token_text}."""
    sentences = re.split(r'(?<=[.!?]) +', story)
    doc_map = {}
    doc_id = 1
    for sent in sentences:
        for token in sent.split():
            doc_map[doc_id] = token
            doc_id += 1
    return doc_map


def find_token_span(doc_map, target_tokens):
    """Locate target_tokens (list of words) inside the story. Returns
    (start, end) as 1-indexed doc ids, or (None, None) if not found."""
    tokens = list(doc_map.values())
    n = len(target_tokens)
    if n == 0:
        return None, None
    for i in range(len(tokens) - n + 1):
        if tokens[i:i + n] == target_tokens:
            return i + 1, i + n
    return None, None


def extract_json(text):
    """Forgiving JSON extraction: strip markdown fences, parse the whole
    thing, wrap a bare object into a list. Falls back to the first [...]."""
    if not text:
        return []
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r'^```(?:json)?\s*\n?', '', s)
        s = re.sub(r'\n?```\s*$', '', s).strip()
    try:
        obj = json.loads(s)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            return [obj]
    except Exception:
        pass
    m = re.search(r'\[.*\]', s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            return []
    return []


def as_token_list(tokens):
    """TOKENS may be a JSON list (["30"]) or a plain string ("30 - point").
    Return a list of words either way."""
    if isinstance(tokens, list):
        return [str(t) for t in tokens]
    if isinstance(tokens, str):
        return tokens.split()
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="raw JSONL to rebuild from")
    ap.add_argument("--games", required=True, help="games CSV with TEXT_ID + GENERATED_TEXT")
    ap.add_argument("--out", required=True, help="output CSV path")
    ap.add_argument("--model", default="", help="MODEL column value")
    ap.add_argument("--prompt_key", default="", help="PROMPT_KEY column value")
    args = ap.parse_args()

    games = pd.read_csv(args.games)
    stories = dict(zip(games["TEXT_ID"], games["GENERATED_TEXT"]))
    doc_maps = {tid: build_doc_token_map(story) for tid, story in stories.items()}

    rows = []
    ann_counter = {}            # per-text auto ANNOTATION_ID when missing
    with open(args.raw) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            text_id = rec.get("text_id")
            line_sent_id = rec.get("sentence_id")   # present only in sentence mode
            for ann in extract_json(rec.get("raw_output", "")):
                if not isinstance(ann, dict):
                    continue
                tid = ann.get("TEXT_ID", text_id)
                tokens = as_token_list(ann.get("TOKENS"))
                if not tokens:
                    continue
                # Sentence mode: trust our loop's sentence id, not the model's.
                sent_id = line_sent_id if line_sent_id is not None else ann.get("SENTENCE_ID")
                # ANNOTATION_ID: use the model's if given, else auto-number.
                if ann.get("ANNOTATION_ID") is not None:
                    aid = ann["ANNOTATION_ID"]
                else:
                    ann_counter[tid] = ann_counter.get(tid, 0) + 1
                    aid = ann_counter[tid]
                # DOC positions: compute from the story exactly like grove_pipeline.
                start, end = find_token_span(doc_maps.get(tid, {}), tokens)
                rows.append({
                    "TEXT_ID": tid,
                    "SENTENCE_ID": sent_id,
                    "ANNOTATION_ID": aid,
                    "TOKENS": " ".join(tokens),
                    "DOC_TOKEN_START": start,
                    "DOC_TOKEN_END": end,
                    "TYPE": ann.get("TYPE"),
                    "CORRECTION": ann.get("CORRECTION"),
                    "COMMENT": ann.get("COMMENT"),
                })

    df = pd.DataFrame(rows)
    df["MODEL"] = args.model
    df["PROMPT_KEY"] = args.prompt_key
    df["TIME_SECONDS"] = ""
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"{os.path.basename(args.out)}: {len(df)} annotations recovered")


if __name__ == "__main__":
    main()
