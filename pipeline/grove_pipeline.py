"""
LLM annotation pipeline (runs on Grove HPC).

This is the script that actually calls the language model on every NBA
game summary and asks it to find factual mistakes. It supports two
modes via --by_sent:

  --by_sent no   (default)  One LLM call per story. Faster, simpler.
  --by_sent yes             One LLM call per sentence. Slower but lets us
                            see how the model performs on early vs late
                            sentences, and removes the chance of the LLM
                            mixing up sentence ids on long stories.

Output files (always two per run):
  results/llm_raw/raw_outputs_<model>_<prompt_key>_run<N>.jsonl
      One line per LLM call. Stores the raw text the model produced
      plus metadata. Useful for re-parsing without re-running the LLM.
  results/llm_csv/results_<model>_<prompt_key>_run<N>.csv
      The parsed annotations, ready to feed into format_converter.

When --by_sent yes is used, <prompt_key> is e.g. "p0_sent" so files
from the two modes never overwrite each other.

Example call:
  python3 grove_pipeline.py \\
      --games games_30_rows.csv \\
      --jsonl shared_task.jsonl \\
      --model llama_medium \\
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
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

# ----- CLI args --------------------------------------------------------------
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--games", type=str, required=True,
                        help="CSV with TEXT_ID + GENERATED_TEXT columns (the stories).")
arg_parser.add_argument("--jsonl", type=str, required=True,
                        help="JSONL with one game-data record per story (box score).")
arg_parser.add_argument("--model", type=str, default="llama_medium")
arg_parser.add_argument("--rows", type=int, default=20,
                        help="How many stories from the top of --games to process.")
arg_parser.add_argument("--prompt", type=str, default="p0", choices=["p0", "p0a","p0b","p0c", "p1", "p2", "p3", "p4"])
arg_parser.add_argument("--by_sent", type=str, default="no", choices=["yes", "no"],
                        help="yes = one LLM call per sentence; no = one LLM call per story")
args = arg_parser.parse_args()

# Model path on Grove. Adjust if you add more checkpoints.
MODELS = {
    "llama_medium": "/home/support/llm/Llama-3.1-70B-Instruct",
    "qwen_medium":  "/home/support/llm/Qwen2.5-72B-Instruct",
    "llama_small":  "/home/support/llm/Llama-3.1-8B-Instruct",
    # qwen 7B isn't in the shared dir, so each of us downloads it to our own
    # home — expanduser resolves ~ to whoever is running (ajain or hahire).
    "qwen_small":   os.path.expanduser("~/models/Qwen2.5-7B-Instruct"),
}


# ----- Pydantic schema for parsing the LLM's JSON output ---------------------
class Annotation(BaseModel):
    """One mistake the LLM has found in a story."""
    TEXT_ID: str
    SENTENCE_ID: int
    ANNOTATION_ID: int
    TOKENS: List[str]
    TYPE: Optional[str] = None
    CORRECTION: Optional[str] = None
    COMMENT: Optional[str] = None


class AnnotationList(RootModel[List[Annotation]]):
    """LangChain needs a RootModel to handle a top-level JSON list."""
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
    """Try hard to pull a JSON list of annotations out of the LLM's reply.

    The LLM can be messy: it might wrap the JSON in a markdown code
    fence, prepend "Here are the mistakes:", or even return a single
    object instead of a list. This function handles those cases."""
    if not text:
        return "[]"
    stripped = text.strip()

    # 1. Strip markdown code fences if present (```json ... ``` or ``` ... ```).
    if stripped.startswith("```"):
        stripped = re.sub(r'^```(?:json)?\s*\n?', '', stripped)
        stripped = re.sub(r'\n?```\s*$', '', stripped).strip()

    # 2. Try to parse the whole thing as JSON. If it's already a list,
    #    keep it. If it's a single object, wrap it in a list — Pydantic
    #    expects a list of annotations.
    try:
        obj = json.loads(stripped)
        if isinstance(obj, list):
            return json.dumps(obj)
        if isinstance(obj, dict):
            return json.dumps([obj])
    except Exception:
        pass

    # 3. Last resort: find the first '[' and the last ']' and hope for the best.
    match = re.search(r'\[.*\]', stripped, re.DOTALL)
    return match.group() if match else "[]"


# ----- Token mapping helpers (used to fill DOC_TOKEN_START/END columns) ------
def build_doc_token_map(text_id, story):
    """Walk the story word by word and build a dict that maps each
    document-level token id (1-indexed) to its sentence id and the
    token's position within that sentence.

    Example entry: { 18: {"sentence_id": 2, "token_id": 4, "token": "Wednesday"} }
    """
    sentences = re.split(r'(?<=[.!?]) +', story)
    doc_map = {}
    doc_token_id = 1
    for sent_id, sent in enumerate(sentences, start=1):
        for tok_id, token in enumerate(sent.split(), start=1):
            doc_map[doc_token_id] = {"sentence_id": sent_id, "token_id": tok_id, "token": token}
            doc_token_id += 1
    return doc_map


def find_token_span(doc_map, target_tokens):
    """Locate target_tokens (a list of words) inside the story's token list.
    Returns (start, end) as 1-indexed doc token ids, or (None, None) if
    the exact word sequence does not appear in the story."""
    tokens = [v["token"] for v in doc_map.values()]
    target_len = len(target_tokens)
    for i in range(len(tokens)):
        if tokens[i:i + target_len] == target_tokens:
            return i + 1, i + target_len
    return None, None


# ----- Load the model --------------------------------------------------------
model_key = args.model
model_name = MODELS[model_key]

print(f"Loading {model_name}...")

tokenizer = AutoTokenizer.from_pretrained(model_name)

# 4-bit quantisation so the 70B / 72B models fit in 2 x RTX A6000.
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
)

# device_map="auto" spreads the layers across the two GPUs. The
# max_memory caps stop the loader from grabbing more than we want.
llm = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    max_memory={0: "25GiB", 1: "46GiB"},
    quantization_config=bnb_config,
)

print("Model loaded.")


def prompt_fn(prompt_key, **vars):
    """Send one prompt to the LLM and return (parsed_annotations,
    raw_text, is_valid_json).

    Works for both modes: callers pass the right keyword args
    (`story=...` for full-story, `sentence=..., sentence_id=...` for
    sentence-by-sentence) and this function forwards them to the
    template.
    """
    template = build_prompt(prompt_key)
    prompt = template.format(**vars)

    # Wrap in the chat-template the model was trained on.
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(llm.device)

    # Greedy decoding, no sampling — deterministic outputs make re-runs comparable.
    with torch.no_grad():
        outputs = llm.generate(**inputs, max_new_tokens=2048, do_sample=False)

    # Slice off the input portion so raw_text is just the model's reply.
    raw_text = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    # Pull JSON out, check if it parses, then try the Pydantic schema.
    extracted = extract_json(raw_text)

    is_valid_json = False
    try:
        json.loads(extracted)
        is_valid_json = True
    except Exception:
        is_valid_json = False

    try:
        parsed = parser.parse(extracted)
    except Exception:
        # Parser couldn't make sense of it — fall back to an empty list
        # so the caller can still proceed without crashing.
        parsed = parser.parse("[]")

    return parsed, raw_text, is_valid_json


# ----- Load the stories + game data into one DataFrame -----------------------
games_df = pd.read_csv(args.games)
game_data_lines = []
with open(args.jsonl, "r") as f:
    for line in f:
        if line.strip():
            game_data_lines.append(line.strip())
# Pair the JSONL lines with the rows of the games CSV (one per game).
games_df["game_data"] = game_data_lines[:len(games_df)]


# ----- Run -------------------------------------------------------------------
all_results = []

# Build the prompt key once. In sentence mode this adds "_sent" so the
# output file names tell the two modes apart.
by_sent = (args.by_sent == "yes")
prompt_key = args.prompt + ("_sent" if by_sent else "")
print(f"Mode: {'sentence-by-sentence' if by_sent else 'full-story'} | prompt={prompt_key}")

# Figure out the next run number so we never overwrite a previous run.
raw_outputs_dir = "results/llm_raw"
os.makedirs(raw_outputs_dir, exist_ok=True)
existing = [f for f in os.listdir(raw_outputs_dir) if f.startswith(f"raw_outputs_{model_key}_{prompt_key}_run")]
run_num = len(existing) + 1
raw_outputs_path = os.path.join(raw_outputs_dir, f"raw_outputs_{model_key}_{prompt_key}_run{run_num}.jsonl")
start_time = time.time()

# Main loop over stories.
for i, row in games_df.head(args.rows).iterrows():
    text_id = row["TEXT_ID"]
    story = row["GENERATED_TEXT"]
    game_data = row["game_data"]

    print(f"Processing {text_id}...")

    # Build the doc-level token map once per story. find_token_span uses
    # it to locate every annotation's word positions inside the full text.
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

                # One raw JSONL line per sentence so we can reconstruct
                # the CSV later even if parsing changes.
                with open(raw_outputs_path, "a") as f:
                    f.write(json.dumps({
                        "text_id": text_id,
                        "sentence_id": sent_id,
                        "prompt_key": prompt_key,
                        "is_valid_json": is_valid_json,
                        "raw_output": raw_text,
                    }) + "\n")

                # The LLM sometimes mislabels SENTENCE_ID — force our loop
                # value because we know exactly which sentence we sent.
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

            # Free GPU memory between sentence calls — these add up fast.
            import gc
            gc.collect()
            torch.cuda.empty_cache()
        print("Done")

    else:
        # ----- Full-story mode ------------------------------------------
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

            # Trust the LLM's SENTENCE_ID here (it has the whole story).
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

        import gc
        gc.collect()
        torch.cuda.empty_cache()


# ----- Save CSV --------------------------------------------------------------
elapsed = round(time.time() - start_time, 2)
df_result = pd.DataFrame(all_results)
df_result["MODEL"] = model_key
df_result["PROMPT_KEY"] = prompt_key
df_result["TIME_SECONDS"] = elapsed

csv_dir = "results/llm_csv"
os.makedirs(csv_dir, exist_ok=True)

# Match the run number to the raw JSONL so the pair always lines up.
existing_csv = [f for f in os.listdir(csv_dir) if f.startswith(f"results_{model_key}_{prompt_key}_run")]
csv_run_num = len(existing_csv) + 1
csv_path = os.path.join(csv_dir, f"results_{model_key}_{prompt_key}_run{csv_run_num}.csv")
df_result.to_csv(csv_path, index=False)

print(f"\nDone in {elapsed}s — {len(df_result)} annotations")
print(f"Raw outputs saved to: {raw_outputs_path}")
print(f"CSV saved to: {csv_path}")
