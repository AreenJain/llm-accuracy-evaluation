"""
LLM annotation pipeline (runs locally via Ollama).

Mirror of grove_pipeline.py — same logic, same output format, but
calls a local Ollama model instead of a HuggingFace model on Grove.

Supports two modes via --by_sent:

  --by_sent no   (default)  One LLM call per story.
  --by_sent yes             One LLM call per sentence. Slower but removes
                            the chance of the LLM mixing up sentence ids
                            on long stories.

Output files (always two per run):
  results/llm_raw/raw_outputs_<model>_<prompt_key>_run<N>.jsonl
  results/llm_csv/results_<model>_<prompt_key>_run<N>.csv

Example call:
  python3 ollama_pipeline.py \\
      --games games_30_rows.csv \\
      --jsonl shared_task.jsonl \\
      --model llama_small \\
      --rows 30 \\
      --prompt p0 \\
      --by_sent yes
"""

import re
from prompts import PROMPTS
import time
import json
import argparse
import pandas as pd
import os
from typing import List, Optional
from pydantic import BaseModel, RootModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import ollama

# ----- CLI args --------------------------------------------------------------
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--games", type=str, required=True,
                        help="CSV with TEXT_ID + GENERATED_TEXT columns (the stories).")
arg_parser.add_argument("--jsonl", type=str, required=True,
                        help="JSONL with one game-data record per story (box score).")
arg_parser.add_argument("--model", type=str, default="llama_small", choices=["llama_small", "qwen_small"])
arg_parser.add_argument("--rows", type=int, default=30,
                        help="How many stories from the top of --games to process.")
arg_parser.add_argument("--prompt", type=str, default="p0", choices=["p0", "p1", "p2", "p3"])
arg_parser.add_argument("--by_sent", type=str, default="no", choices=["yes", "no"],
                        help="yes = one LLM call per sentence; no = one LLM call per story")
args = arg_parser.parse_args()

# Ollama model name map — must match what you have pulled locally.
# Run: ollama pull llama3.1   or   ollama pull qwen2.5
MODELS = {
    "llama_small": "llama3.1:8b",
    "qwen_small":  "qwen2.5:7b",
}


# ----- Pydantic schema -------------------------------------------------------
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


def build_prompt(prompt_key):
    """Build a LangChain PromptTemplate for the chosen prompt key.

    Sentence-mode prompts (ending in '_sent') take a single sentence
    plus its 1-indexed id; story-mode prompts take the full story."""
    if prompt_key.endswith("_sent"):
        ivs = ["text_id", "sentence", "sentence_id", "game_data"]
    else:
        ivs = ["text_id", "story", "game_data"]
    return PromptTemplate(
        template=PROMPTS[prompt_key],
        input_variables=ivs,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )


def extract_json(text):
    """Pull a JSON list out of the LLM's raw reply.

    Handles markdown code fences, single-object responses, and
    conversational preamble — same logic as grove_pipeline."""
    if not text:
        return "[]"
    stripped = text.strip()

    # Strip markdown code fences if present.
    if stripped.startswith("```"):
        stripped = re.sub(r'^```(?:json)?\s*\n?', '', stripped)
        stripped = re.sub(r'\n?```\s*$', '', stripped).strip()

    # Try to parse whole thing as JSON first.
    try:
        obj = json.loads(stripped)
        if isinstance(obj, list):
            return json.dumps(obj)
        if isinstance(obj, dict):
            return json.dumps([obj])
    except Exception:
        pass

    # Last resort: grab first [...] block.
    match = re.search(r'\[.*\]', stripped, re.DOTALL)
    return match.group() if match else "[]"


# ----- Token mapping helpers -------------------------------------------------
def build_doc_token_map(text_id, story):
    """Walk the story word by word and build a dict mapping each
    document-level token id (1-indexed) to sentence id + local position."""
    sentences = re.split(r'(?<=[.!?]) +', story)
    doc_map = {}
    doc_token_id = 1
    for sent_id, sent in enumerate(sentences, start=1):
        for tok_id, token in enumerate(sent.split(), start=1):
            doc_map[doc_token_id] = {"sentence_id": sent_id, "token_id": tok_id, "token": token}
            doc_token_id += 1
    return doc_map


def find_token_span(doc_map, target_tokens):
    """Locate target_tokens inside the story token list.
    Returns (start, end) as 1-indexed doc token ids, or (None, None)."""
    tokens = [v["token"] for v in doc_map.values()]
    target_len = len(target_tokens)
    for i in range(len(tokens)):
        if tokens[i:i + target_len] == target_tokens:
            return i + 1, i + target_len
    return None, None


# ----- Model setup -----------------------------------------------------------
model_key = args.model
model_name = MODELS[model_key]

print(f"Using Ollama model: {model_name}")
print("Make sure Ollama is running locally (ollama serve) and the model is pulled.")


def prompt_fn(prompt_key, **vars):
    """Send one prompt to Ollama and return (parsed_annotations,
    raw_text, is_valid_json).

    Accepts keyword args so both modes work:
      story mode:    prompt_fn(prompt_key, text_id=..., story=..., game_data=...)
      sentence mode: prompt_fn(prompt_key, text_id=..., sentence=..., sentence_id=..., game_data=...)
    """
    template = build_prompt(prompt_key)
    prompt = template.format(**vars)

    response = ollama.chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}]
    )
    raw_text = response["message"]["content"]

    extracted = extract_json(raw_text)

    is_valid_json = False
    try:
        json.loads(extracted)
        is_valid_json = True
    except Exception:
        pass

    try:
        parsed = parser.parse(extracted)
    except Exception:
        parsed = parser.parse("[]")

    return parsed, raw_text, is_valid_json


# ----- Load data -------------------------------------------------------------
games_df = pd.read_csv(args.games)
game_data_lines = []
with open(args.jsonl, "r") as f:
    for line in f:
        if line.strip():
            game_data_lines.append(line.strip())
games_df["game_data"] = game_data_lines[:len(games_df)]


# ----- Run -------------------------------------------------------------------
all_results = []

by_sent = (args.by_sent == "yes")
prompt_key = args.prompt + ("_sent" if by_sent else "")
print(f"Mode: {'sentence-by-sentence' if by_sent else 'full-story'} | prompt={prompt_key}")

raw_outputs_dir = "results/llm_raw"
os.makedirs(raw_outputs_dir, exist_ok=True)
existing = [f for f in os.listdir(raw_outputs_dir) if f.startswith(f"raw_outputs_{model_key}_{prompt_key}_run")]
run_num = len(existing) + 1
raw_outputs_path = os.path.join(raw_outputs_dir, f"raw_outputs_{model_key}_{prompt_key}_run{run_num}.jsonl")

start_time = time.time()

for i, row in games_df.head(args.rows).iterrows():
    text_id = row["TEXT_ID"]
    story = row["GENERATED_TEXT"]
    game_data = row["game_data"]

    print(f"Processing {text_id}...")

    doc_map = build_doc_token_map(text_id, story)

    if by_sent:
        # ----- Sentence-by-sentence mode ---------------------------------
        sentences = re.split(r'(?<=[.!?]) +', story)
        for sent_id, sent_text in enumerate(sentences, start=1):
            try:
                parsed, raw_text, is_valid_json = prompt_fn(
                    prompt_key,
                    text_id=text_id,
                    sentence=sent_text,
                    sentence_id=sent_id,
                    game_data=game_data,
                )

                with open(raw_outputs_path, "a") as f:
                    f.write(json.dumps({
                        "text_id": text_id,
                        "sentence_id": sent_id,
                        "prompt_key": prompt_key,
                        "is_valid_json": is_valid_json,
                        "raw_output": raw_text,
                    }) + "\n")

                # Force our loop sentence_id — the LLM only saw one sentence
                # so its SENTENCE_ID is often wrong or just "1".
                for ann in parsed.root:
                    start, end = find_token_span(doc_map, ann.TOKENS)
                    all_results.append({
                        "TEXT_ID": text_id,
                        "SENTENCE_ID": sent_id,
                        "ANNOTATION_ID": ann.ANNOTATION_ID,
                        "TOKENS": " ".join(ann.TOKENS),
                        "DOC_TOKEN_START": start,
                        "DOC_TOKEN_END": end,
                        "TYPE": ann.TYPE,
                        "CORRECTION": ann.CORRECTION,
                        "COMMENT": ann.COMMENT,
                    })
                print(f"  sent {sent_id}: valid={is_valid_json}, {len(parsed.root)} ann")
            except Exception as e:
                print(f"  sent {sent_id} failed: {e}")
        print("Done")

    else:
        # ----- Full-story mode -------------------------------------------
        try:
            parsed, raw_text, is_valid_json = prompt_fn(
                prompt_key,
                text_id=text_id,
                story=story,
                game_data=game_data,
            )

            with open(raw_outputs_path, "a") as f:
                f.write(json.dumps({
                    "text_id": text_id,
                    "prompt_key": prompt_key,
                    "is_valid_json": is_valid_json,
                    "raw_output": raw_text,
                }) + "\n")

            print(f"  JSON valid: {is_valid_json}")

            for ann in parsed.root:
                start, end = find_token_span(doc_map, ann.TOKENS)
                all_results.append({
                    "TEXT_ID": text_id,
                    "SENTENCE_ID": ann.SENTENCE_ID,
                    "ANNOTATION_ID": ann.ANNOTATION_ID,
                    "TOKENS": " ".join(ann.TOKENS),
                    "DOC_TOKEN_START": start,
                    "DOC_TOKEN_END": end,
                    "TYPE": ann.TYPE,
                    "CORRECTION": ann.CORRECTION,
                    "COMMENT": ann.COMMENT,
                })
            print("Done")
        except Exception as e:
            print(f"{text_id} failed: {e}")


# ----- Save CSV --------------------------------------------------------------
elapsed = round(time.time() - start_time, 2)
df_result = pd.DataFrame(all_results)
df_result["MODEL"] = model_key
df_result["PROMPT_KEY"] = prompt_key
df_result["TIME_SECONDS"] = elapsed

csv_dir = "results/llm_csv"
os.makedirs(csv_dir, exist_ok=True)
existing_csv = [f for f in os.listdir(csv_dir) if f.startswith(f"results_{model_key}_{prompt_key}_run")]
csv_run_num = len(existing_csv) + 1
csv_path = os.path.join(csv_dir, f"results_{model_key}_{prompt_key}_run{csv_run_num}.csv")
df_result.to_csv(csv_path, index=False)

print(f"\nDone in {elapsed}s — {len(df_result)} annotations")
print(f"Raw outputs saved to: {raw_outputs_path}")
print(f"CSV saved to: {csv_path}")