"""
Reprocess a raw_outputs JSONL file (sentence-mode or full-story) into a results CSV.

Used when grove_pipeline.py wrote an empty CSV because extract_json failed
(e.g. p0 prompt where Llama returned a bare object instead of a JSON list).

Usage:
    python3 evaluation/reprocess_raw.py \
        --raw "results/llm_raw/raw_outputs_llama_medium_p0_sent_run1.jsonl" \
        --games "data/games_30_rows.csv" \
        --out "results/llm_csv/results_llama_medium_p0_sent_run1.csv"

No LLM calls are made — only re-parses the stored raw_output strings.
"""

import argparse
import json
import os
import re
from typing import List, Optional

import pandas as pd
from pydantic import BaseModel, RootModel
from langchain_core.output_parsers import PydanticOutputParser


class Annotation(BaseModel):
    TEXT_ID: str
    SENTENCE_ID: int
    ANNOTATION_ID: int
    TOKENS: List[str]
    TYPE: Optional[str] = None
    CORRECTION: Optional[str] = None
    COMMENT: Optional[str] = None


class AnnotationList(RootModel[List[Annotation]]):
    pass


parser = PydanticOutputParser(pydantic_object=AnnotationList)


def extract_json(text):
    """Same logic as the fixed grove_pipeline.extract_json."""
    if not text:
        return "[]"
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r'^```(?:json)?\s*\n?', '', stripped)
        stripped = re.sub(r'\n?```\s*$', '', stripped).strip()
    try:
        obj = json.loads(stripped)
        if isinstance(obj, list):
            return json.dumps(obj)
        if isinstance(obj, dict):
            return json.dumps([obj])
    except Exception:
        pass
    match = re.search(r'\[.*\]', stripped, re.DOTALL)
    return match.group() if match else "[]"


def build_doc_token_map(story):
    sentences = re.split(r'(?<=[.!?]) +', story)
    doc_map = {}
    doc_token_id = 1
    for sent_id, sent in enumerate(sentences, start=1):
        for tok_id, token in enumerate(sent.split(), start=1):
            doc_map[doc_token_id] = {"sentence_id": sent_id, "token_id": tok_id, "token": token}
            doc_token_id += 1
    return doc_map


def find_token_span(doc_map, target_tokens):
    tokens = [v["token"] for v in doc_map.values()]
    n = len(target_tokens)
    for i in range(len(tokens)):
        if tokens[i:i + n] == target_tokens:
            return i + 1, i + n
    return None, None


def parse_run_id_from_path(raw_path):
    """raw_outputs_llama_medium_p0_sent_run1.jsonl -> (model_key, prompt_key)."""
    base = os.path.basename(raw_path).replace(".jsonl", "")
    rest = base[len("raw_outputs_"):]
    rest = re.sub(r'_run\d+$', '', rest)
    parts = rest.split("_")
    model_key = "_".join(parts[:2])
    prompt_key = "_".join(parts[2:])
    return model_key, prompt_key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="path to raw_outputs_*.jsonl")
    ap.add_argument("--games", required=True, help="games csv with TEXT_ID + GENERATED_TEXT")
    ap.add_argument("--out", required=True, help="output csv path")
    args = ap.parse_args()

    model_key, prompt_key = parse_run_id_from_path(args.raw)
    print(f"Parsed from filename -> model={model_key}, prompt_key={prompt_key}")

    games_df = pd.read_csv(args.games)
    stories = dict(zip(games_df["TEXT_ID"], games_df["GENERATED_TEXT"]))
    print(f"Loaded {len(stories)} stories from {args.games}")

    doc_maps = {}
    all_results = []
    n_lines = 0
    n_valid = 0
    n_anns = 0
    n_parse_fail = 0
    n_no_pos = 0

    with open(args.raw) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n_lines += 1
            try:
                rec = json.loads(line)
            except Exception as e:
                print(f"  bad jsonl line {n_lines}: {e}")
                continue

            text_id = rec["text_id"]
            sent_id = rec.get("sentence_id")
            raw_output = rec.get("raw_output", "")

            extracted = extract_json(raw_output)
            try:
                parsed = parser.parse(extracted)
                n_valid += 1
            except Exception:
                n_parse_fail += 1
                parsed = parser.parse("[]")

            if text_id not in doc_maps:
                if text_id not in stories:
                    print(f"  no story for {text_id}, skipping")
                    continue
                doc_maps[text_id] = build_doc_token_map(stories[text_id])
            doc_map = doc_maps[text_id]

            for ann in parsed.root:
                start, end = find_token_span(doc_map, ann.TOKENS)
                if start is None:
                    n_no_pos += 1
                sentence_id_out = sent_id if sent_id is not None else ann.SENTENCE_ID
                all_results.append({
                    "TEXT_ID": text_id,
                    "SENTENCE_ID": sentence_id_out,
                    "ANNOTATION_ID": ann.ANNOTATION_ID,
                    "TOKENS": " ".join(ann.TOKENS),
                    "DOC_TOKEN_START": start,
                    "DOC_TOKEN_END": end,
                    "TYPE": ann.TYPE,
                    "CORRECTION": ann.CORRECTION,
                    "COMMENT": ann.COMMENT,
                })
                n_anns += 1

    df = pd.DataFrame(all_results)
    df["MODEL"] = model_key
    df["PROMPT_KEY"] = prompt_key
    df["TIME_SECONDS"] = 0

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    df.to_csv(args.out, index=False)

    print("-" * 60)
    print(f"JSONL lines read     : {n_lines}")
    print(f"Successfully parsed  : {n_valid}")
    print(f"Parse fallbacks (empty): {n_parse_fail}")
    print(f"Total annotations    : {n_anns}")
    print(f"Annotations w/o pos  : {n_no_pos}")
    print(f"Wrote CSV -> {args.out}")


if __name__ == "__main__":
    main()
