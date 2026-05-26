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

# CLI
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--games", type=str, required=True)
arg_parser.add_argument("--jsonl", type=str, required=True)
arg_parser.add_argument("--model", type=str, default="llama_medium")
arg_parser.add_argument("--rows", type=int, default=20)
arg_parser.add_argument("--prompt", type=str, default="p0", choices=["p0", "p1", "p2", "p3"])
arg_parser.add_argument("--by_sent", type=str, default="no", choices=["yes", "no"],
                        help="yes = one LLM call per sentence; no = one LLM call per story")
args = arg_parser.parse_args()

MODELS = {
    "llama_medium": "/home/support/llm/Llama-3.1-70B-Instruct",
    "qwen_medium":  "/home/support/llm/Qwen2.5-72B-Instruct",
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
    if prompt_key.endswith("_sent"):
        ivs = ["text_id", "sentence", "sentence_id", "game_data"]
    else:
        ivs = ["text_id", "story", "game_data"]
    return PromptTemplate(
        template=PROMPTS[prompt_key],
        input_variables=ivs,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
#function to extract JSON from raw text
def extract_json(text):
    if not text:  # return empty list if text is empty or None
        return "[]"
    stripped = text.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    if stripped.startswith("```"):
        stripped = re.sub(r'^```(?:json)?\s*\n?', '', stripped)
        stripped = re.sub(r'\n?```\s*$', '', stripped).strip()
    # Try parsing the whole stripped text as JSON. If it's a list, keep it.
    # If it's a single object, wrap it in a list (handles loose prompts where
    # the LLM forgets the outer [...]).
    try:
        obj = json.loads(stripped)
        if isinstance(obj, list):
            return json.dumps(obj)
        if isinstance(obj, dict):
            return json.dumps([obj])
    except Exception:
        pass
    # Fallback: old regex (greedy first-[ to last-])
    match = re.search(r'\[.*\]', stripped, re.DOTALL)
    return match.group() if match else "[]"

# Functions for mapping tokens to document positions
def build_doc_token_map(text_id, story): #
    sentences = re.split(r'(?<=[.!?]) +', story) #split story into sentences based on punctuation followed by space
    doc_map = {} 
    doc_token_id = 1 #initialize document token ID
    for sent_id, sent in enumerate(sentences, start=1): #iterate over sentences with sentence ID starting from 1
        for tok_id, token in enumerate(sent.split(), start=1): #iterate over tokens in sentence with token ID starting from 1
            doc_map[doc_token_id] = {"sentence_id": sent_id, "token_id": tok_id, "token": token} #map document token ID to sentence ID, token ID, and token text
            doc_token_id += 1 
    return doc_map

# Function to find token span in document based on target tokens
def find_token_span(doc_map, target_tokens):
    tokens = [v["token"] for v in doc_map.values()] #extract tokens from document map
    target_len = len(target_tokens) #length of target tokens
    for i in range(len(tokens)): 
        if tokens[i:i+target_len] == target_tokens: #check if tokens in document match target tokens
            return i+1, i+target_len #return start and end document token IDs (1-indexed)
    return None, None # tokens not found in document, return None for both start and end

# Load model
model_key = args.model
model_name = MODELS[model_key]

print(f"Loading {model_name}...")

# load the tokenizer for the specified model from local path
tokenizer = AutoTokenizer.from_pretrained(model_name) 

# 4-bit configuration for memory efficiency
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True
)

# load the model with the specified configuration, using bfloat16 for computation and automatically mapping to available devices (GPUs), with specified memory limits for each GPU
llm = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    max_memory={0: "25GiB", 1: "46GiB"},  
    quantization_config=bnb_config
)

print("Model loaded.")

# Main function to call the LLM. Accepts either full-story vars (story=...)
# or sentence vars (sentence=..., sentence_id=...) via **vars.
def prompt_fn(prompt_key, **vars):
    template = build_prompt(prompt_key)
    prompt = template.format(**vars)

    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(llm.device)
    
    # inference mode, no gradient tracking (saves memory)
    with torch.no_grad(): 
        # generate up to 2048 tokens, deterministic (no randomness)
        outputs = llm.generate(**inputs, max_new_tokens=2048, do_sample=False)
    
    # decode tokens to text (everything after the input prompt)
    raw_text = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    
    # extract JSON portion from raw text
    extracted = extract_json(raw_text)
    
    # checking if extracted text is valid JSON
    is_valid_json = False
    try:
        json.loads(extracted)
        is_valid_json = True
    except Exception:
        is_valid_json = False
    
    # parse the extracted JSON using the Pydantic parser
    try:
        parsed = parser.parse(extracted)
    except Exception:
        parsed = parser.parse("[]")
    
    return parsed, raw_text, is_valid_json

# Load data
games_df = pd.read_csv(args.games)
game_data_lines = []

# read JSONL file, strip whitespace, store non-empty lines
with open(args.jsonl, "r") as f:
    for line in f:
        if line.strip():
            game_data_lines.append(line.strip())  # add cleaned non-empty line to list
# add game_data as new column in dataframe (only as many rows as games_df has)
games_df["game_data"] = game_data_lines[:len(games_df)]  

# Run
all_results = []

# Decide mode + prompt key first so filenames carry the suffix when by_sent=yes
by_sent = (args.by_sent == "yes")
prompt_key = args.prompt + ("_sent" if by_sent else "")
print(f"Mode: {'sentence-by-sentence' if by_sent else 'full-story'} | prompt={prompt_key}")

#directory to save raw outputs from the model
raw_outputs_dir = "results/llm_raw"
# create folder if it doesn't exist (no error if already there)
os.makedirs(raw_outputs_dir, exist_ok=True)
# list existing run files for this model + prompt_key combo
existing = [f for f in os.listdir(raw_outputs_dir) if f.startswith(f"raw_outputs_{model_key}_{prompt_key}_run")]
# next run number = count of existing + 1
run_num = len(existing) + 1
# build full file path with run number
raw_outputs_path = os.path.join(raw_outputs_dir, f"raw_outputs_{model_key}_{prompt_key}_run{run_num}.jsonl")
start_time = time.time()  # record start time to measure total elapsed time later

# iterate over rows of the dataframe, processing only the number of rows specified by --rows argument
for i, row in games_df.head(args.rows).iterrows():
    text_id = row["TEXT_ID"]
    story = row["GENERATED_TEXT"]
    game_data = row["game_data"]

    print(f"Processing {text_id}...")

    # build position map of every word in story (built ONCE per story; reused
    # for every sentence call when by_sent=yes)
    doc_map = build_doc_token_map(text_id, story)

    if by_sent:
        # split into sentences using the same regex as build_doc_token_map
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

                # raw JSONL line has an extra sentence_id field
                with open(raw_outputs_path, "a") as f:
                    f.write(json.dumps({
                        "text_id": text_id,
                        "sentence_id": sent_id,
                        "prompt_key": prompt_key,
                        "is_valid_json": is_valid_json,
                        "raw_output": raw_text,
                    }) + "\n")

                for ann in parsed.root:
                    start, end = find_token_span(doc_map, ann.TOKENS)
                    all_results.append({
                        "TEXT_ID": text_id,
                        "SENTENCE_ID": sent_id,  # force loop value, ignore LLM's
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
            import gc
            gc.collect()
            torch.cuda.empty_cache()
        print("Done")
    else:
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

        import gc
        gc.collect()
        torch.cuda.empty_cache()

# After processing all rows, calculate total elapsed time and save results to a CSV file with metadata (model name and time taken)
elapsed = round(time.time() - start_time, 2)
df_result = pd.DataFrame(all_results)
df_result["MODEL"] = model_key
df_result["PROMPT_KEY"] = prompt_key
df_result["TIME_SECONDS"] = elapsed


csv_dir = "results/llm_csv"  # folder name for CSV outputs
os.makedirs(csv_dir, exist_ok=True)  # create folder if not exists
# list existing CSV runs for this model
existing_csv = [f for f in os.listdir(csv_dir) if f.startswith(f"results_{model_key}_{prompt_key}_run")]
csv_run_num = len(existing_csv) + 1  # next run number for CSV
csv_path = os.path.join(csv_dir, f"results_{model_key}_{prompt_key}_run{csv_run_num}.csv") # build full CSV file path
df_result.to_csv(csv_path, index=False)

print(f"\nDone in {elapsed}s — {len(df_result)} annotations")
print(f"Raw outputs saved to: {raw_outputs_path}")
print(f"CSV saved to: {csv_path}")
