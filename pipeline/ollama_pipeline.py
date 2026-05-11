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
import ollama  # pip install ollama

# CLI
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--games", type=str, required=True)
arg_parser.add_argument("--jsonl", type=str, required=True)
arg_parser.add_argument("--model", type=str, default="llama_small", choices=["llama_small", "qwen_small"])
arg_parser.add_argument("--rows", type=int, default=30)
arg_parser.add_argument("--prompt", type=str, default="p0", choices=["p0", "p1", "p2", "p3", "p4"])
args = arg_parser.parse_args()

# Ollama model name map  — must match what you have pulled locally
# Run: ollama pull llama3.1     or     ollama pull qwen2.5
MODELS = {
    "llama_small": "llama3.1:8b",
    "qwen_small":  "qwen2.5:7b",
}

# Pydantic
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
    return PromptTemplate(
        template=PROMPTS[prompt_key],
        input_variables=["text_id", "story", "game_data"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

# Extract JSON array from raw model output text
def extract_json(text):
    if not text:
        return "[]"
    match = re.search(r'\[.*\]', text, re.DOTALL)
    return match.group() if match else "[]"

# Build a map of every token in the story to its sentence + position
def build_doc_token_map(text_id, story):
    sentences = re.split(r'(?<=[.!?]) +', story)
    doc_map = {}
    doc_token_id = 1
    for sent_id, sent in enumerate(sentences, start=1):
        for tok_id, token in enumerate(sent.split(), start=1):
            doc_map[doc_token_id] = {"sentence_id": sent_id, "token_id": tok_id, "token": token}
            doc_token_id += 1
    return doc_map

# Find where a list of tokens appears in the document and return start/end positions
def find_token_span(doc_map, target_tokens):
    tokens = [v["token"] for v in doc_map.values()]
    target_len = len(target_tokens)
    for i in range(len(tokens)):
        if tokens[i:i + target_len] == target_tokens:
            return i + 1, i + target_len  # 1-indexed
    return None, None

# Resolve which Ollama model name to use
model_key = args.model
model_name = MODELS[model_key]

print(f"Using Ollama model: {model_name}")
print("Make sure Ollama is running locally (ollama serve) and the model is pulled.")

# Main inference function — calls Ollama instead of HuggingFace
def prompt_fn(text_id, story, game_data, prompt_key):
    template = build_prompt(prompt_key)
    prompt = template.format(text_id=text_id, story=story, game_data=game_data)

    # Call local Ollama model
    response = ollama.chat(
        model=model_name,
        messages=[{"role": "user", "content": prompt}]
    )

    # Extract the raw text response from Ollama
    raw_text = response["message"]["content"]

    extracted = extract_json(raw_text)

    # Check if extracted text is valid JSON
    is_valid_json = False
    try:
        json.loads(extracted)
        is_valid_json = True
    except Exception:
        is_valid_json = False

    # Parse with Pydantic, fall back to empty list on failure
    try:
        parsed = parser.parse(extracted)
    except Exception:
        parsed = parser.parse("[]")

    return parsed, raw_text, is_valid_json

# Load data
games_df = pd.read_csv(args.games)
game_data_lines = []

with open(args.jsonl, "r") as f:
    for line in f:
        if line.strip():
            game_data_lines.append(line.strip())

games_df["game_data"] = game_data_lines[:len(games_df)]

# Run
all_results = []
raw_outputs_dir = "LLM Raw results"
os.makedirs(raw_outputs_dir, exist_ok=True)

existing = [f for f in os.listdir(raw_outputs_dir) if f.startswith(f"raw_outputs_{model_key}_{args.prompt}_run")]
run_num = len(existing) + 1
raw_outputs_path = os.path.join(raw_outputs_dir, f"raw_outputs_{model_key}_{args.prompt}_run{run_num}.jsonl")

start_time = time.time()

for i, row in games_df.head(args.rows).iterrows():
    text_id = row["TEXT_ID"]
    story = row["GENERATED_TEXT"]
    game_data = row["game_data"]

    print(f"Processing {text_id}...")

    try:
        parsed, raw_text, is_valid_json = prompt_fn(text_id, story, game_data, args.prompt)

        with open(raw_outputs_path, "a") as f:
            f.write(json.dumps({
                "text_id": text_id,
                "is_valid_json": is_valid_json,
                "raw_output": raw_text
            }) + "\n")

        print(f"  JSON valid: {is_valid_json}")

        doc_map = build_doc_token_map(text_id, story)

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

# Save results
elapsed = round(time.time() - start_time, 2)
df_result = pd.DataFrame(all_results)
df_result["MODEL"] = model_key
df_result["TIME_SECONDS"] = elapsed

csv_dir = "LLM_results CSV"
os.makedirs(csv_dir, exist_ok=True)
existing_csv = [f for f in os.listdir(csv_dir) if f.startswith(f"results_{model_key}_{args.prompt}_run")]
csv_run_num = len(existing_csv) + 1
csv_path = os.path.join(csv_dir, f"results_{model_key}_{args.prompt}_run{csv_run_num}.csv")
df_result.to_csv(csv_path, index=False)

print(f"\nDone in {elapsed}s — {len(df_result)} annotations")
print(f"Raw outputs saved to: {raw_outputs_path}")
print(f"CSV saved to: {csv_path}")