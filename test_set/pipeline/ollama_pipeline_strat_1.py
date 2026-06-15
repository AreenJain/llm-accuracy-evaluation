import re
from prompts import PROMPTS
import time
import json
import argparse
import pandas as pd
import os
from typing import List, Optional
from pydantic import BaseModel, RootModel, field_validator
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import ollama
from rapidfuzz import fuzz
import nltk

nltk.download("punkt_tab", quiet=True)

# ----- CLI args --------------------------------------------------------------
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--games", type=str, required=True)
arg_parser.add_argument("--jsonl", type=str, required=True)
arg_parser.add_argument("--model", type=str, default="llama_small", choices=["llama_small", "qwen_small"])
arg_parser.add_argument("--rows", type=int, default=30)
arg_parser.add_argument("--prompt", type=str, default="p0", choices=["p0", "p1", "p2", "p3", "p4"])
arg_parser.add_argument("--by_sent", type=str, default="no", choices=["yes", "no"],
                        help="yes = one LLM call per sentence; no = one LLM call per story")
args = arg_parser.parse_args()

MODELS = {
    "llama_small": "llama3.1:8b",
    "qwen_small":  "qwen2.5:7b",
}

# ----- Tokenizer -------------------------------------------------------------
# FIX 3: Replaced word_tokenize (NLTK) with a simple whitespace+punctuation-aware
# splitter so that hyphenated tokens like "three-point" or "go-ahead" are kept
# as a single token instead of being split into ["three", "-", "point"].
# This makes the doc_map consistent with what the LLM copies verbatim from the story.
#
# Strategy: split on whitespace, then for each chunk strip leading/trailing
# punctuation but keep internal punctuation (hyphens, apostrophes, dots in
# abbreviations).  Punctuation-only chunks (commas, periods, quotes) are kept
# as separate tokens so token counts stay accurate.

_PUNCT_STRIP = re.compile(r'^["""\'()\[\]{}<>]+|["""\'()\[\]{}<>.,!?;:]+$')

def simple_tokenize(text: str) -> List[str]:
    """
    Whitespace-split, then strip wrapping punctuation while preserving
    internal hyphens/apostrophes.  Empty strings after stripping are dropped.

    Examples
    --------
    "didn't"   -> ["didn't"]      (apostrophe kept)
    "three-point" -> ["three-point"]  (hyphen kept)
    "scored."  -> ["scored", "."]  -- actually we keep trailing dot as own token
    """
    tokens = []
    for raw in text.split():
        # strip only wrapping quotes/brackets; NOT hyphens or apostrophes
        stripped = _PUNCT_STRIP.sub("", raw)
        # if the raw chunk ends with sentence-ending punctuation, split it off
        # so "scored." -> ["scored", "."]
        m = re.match(r'^(.*\w)([.,!?;:]+)$', stripped)
        if m:
            tokens.append(m.group(1))
            tokens.append(m.group(2))
        elif stripped:
            tokens.append(stripped)
        # if stripping left nothing (e.g. raw was just punctuation), keep raw
        elif raw:
            tokens.append(raw)
    return tokens


# ----- Pydantic schema -------------------------------------------------------
class Annotation(BaseModel):
    TEXT_ID: str
    SENTENCE_ID: Optional[int] = None
    ANNOTATION_ID: int
    TOKENS: List[str]
    # FIX 1: Renamed PREFIX -> LEFT_CONTEXT and SUFFIX -> RIGHT_CONTEXT to match
    # the field names expected by find_token_span_with_context().
    # Previously the prompt used PREFIX/SUFFIX but the schema used LEFT_CONTEXT/
    # RIGHT_CONTEXT, so ann.LEFT_CONTEXT was always None and context anchoring
    # never fired.
    LEFT_CONTEXT: Optional[str] = None
    RIGHT_CONTEXT: Optional[str] = None
    TYPE: Optional[str] = None
    CORRECTION: Optional[str] = None
    COMMENT: Optional[str] = None

    # FIX 2: TOKENS coercion — LLMs sometimes return a plain string instead of
    # a JSON array, e.g. "TOKENS": "Stephen Curry" instead of
    # "TOKENS": ["Stephen", "Curry"].
    # Pydantic would either raise a validation error or, worse, iterate the
    # string character-by-character producing ["S","t","e","p","h",...].
    # This validator intercepts a bare string and splits it on whitespace so
    # both formats produce the correct list of tokens.
    @field_validator("TOKENS", mode="before")
    @classmethod
    def coerce_tokens(cls, v):
        if isinstance(v, str):
            # plain string -> split on whitespace, same rule as the tokenizer
            return v.strip().split()
        return v

    # FIX 4 & 5: Context and capitalization normalisation.
    # The LLM is instructed to copy PREFIX/SUFFIX verbatim, but it sometimes:
    #   - lowercases words ("lebron" instead of "LeBron")
    #   - adds/removes punctuation ("scored," vs "scored")
    # We normalise to lowercase+strip-punctuation at match time (in
    # find_token_span_with_context), so no change is needed to the stored
    # value here — we store exactly what the LLM returned so the raw CSV
    # is auditable.  The normalisation happens only during search.

class AnnotationList(RootModel[List[Annotation]]):
    pass

parser = PydanticOutputParser(pydantic_object=AnnotationList)

def build_prompt(prompt_key):
    """Sentence-mode prompts (ending in '_sent') take a single sentence;
    story-mode prompts take the full story."""
    if prompt_key.endswith("_sent"):
        ivs = ["text_id", "sentence", "sentence_id", "game_data"]
    else:
        ivs = ["text_id", "story", "game_data"]
    return PromptTemplate(
        template=PROMPTS[prompt_key],
        input_variables=ivs,
        # partial_variables={"format_instructions": parser.get_format_instructions()}
    )

def extract_json(text):
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

# FIX 4 & 5: normalize_token now also collapses internal hyphens/apostrophes
# so that "three-point" and "threepoint" both normalize to "threepoint", making
# fuzzy matching more tolerant of minor punctuation differences from the LLM.
# Lowercasing handles all capitalisation mismatches ("LeBron" == "lebron").
def normalize_token(token: str) -> str:
    return re.sub(r"[^\w]", "", token.lower())

# FIX 4 (context matching): normalize_context strips punctuation and lowercases
# the entire PREFIX/SUFFIX string before checking if it appears in the window.
# This means "scored," and "Scored" and "scored" all match identically.
def normalize_context(ctx: str) -> str:
    return re.sub(r"[^\w\s]", "", ctx.lower()).strip()


def build_doc_token_map(text_id, story):
    # FIX 3: use simple_tokenize instead of word_tokenize so that hyphenated
    # basketball tokens ("three-point", "go-ahead", "76ers") are not split.
    sentences = re.split(r'(?<=[.!?]) +', story)
    doc_map = {}
    doc_token_id = 1
    for sent_id, sent in enumerate(sentences, start=1):
        tokens = simple_tokenize(sent)   # <-- changed from word_tokenize
        for tok_id, token in enumerate(tokens, start=1):
            doc_map[doc_token_id] = {
                "sentence_id": sent_id,
                "token_id": tok_id,
                "token": token
            }
            doc_token_id += 1
    return doc_map


def find_token_span_with_context(
    doc_map,
    target_tokens,
    left_context=None,
    right_context=None,
    window=6,
    fuzzy_threshold=85,   # slightly relaxed from 90 to tolerate capitalisation
                          # differences that survive after normalisation
):
    tokens = [v["token"] for v in doc_map.values()]
    normalized_doc = [normalize_token(t) for t in tokens]
    normalized_target = [normalize_token(t) for t in target_tokens]

    # FIX 2 guard: if coercion produced an empty list (LLM returned ""),
    # bail early rather than returning span (1, 0).
    if not normalized_target:
        return None, None

    target_len = len(normalized_target)
    candidates = []

    for i in range(len(tokens) - target_len + 1):
        span = normalized_doc[i:i + target_len]
        fuzzy_score = fuzz.ratio(" ".join(span), " ".join(normalized_target))
        if fuzzy_score >= fuzzy_threshold:
            score = fuzzy_score

            # FIX 4 & 5: use normalize_context (strips punctuation + lowercase)
            # before checking window membership so capitalisation and trailing
            # commas/periods in PREFIX/SUFFIX don't break the match.
            if left_context:
                left_window = " ".join(
                    normalize_token(t) for t in tokens[max(0, i - window):i]
                )
                # FIX 3 (context): normalize each word of the context string
                # the same way, then check substring membership
                norm_lc = normalize_context(left_context)
                if norm_lc and norm_lc in left_window:
                    score += 20

            if right_context:
                right_window = " ".join(
                    normalize_token(t) for t in tokens[i + target_len:i + target_len + window]
                )
                norm_rc = normalize_context(right_context)
                if norm_rc and norm_rc in right_window:
                    score += 20

            candidates.append((score, i))

    if not candidates:
        return None, None
    candidates.sort(reverse=True)
    best_i = candidates[0][1]
    return best_i + 1, best_i + target_len

# ----- Model setup -----------------------------------------------------------
model_key = args.model
model_name = MODELS[model_key]

print(f"Using Ollama model: {model_name}")
print("Make sure Ollama is running locally (ollama serve) and the model is pulled.")

def prompt_fn(prompt_key, **vars):
    """Accepts keyword args so both modes work:
      story mode:    prompt_fn(prompt_key, text_id=..., story=..., game_data=...)
      sentence mode: prompt_fn(prompt_key, text_id=..., sentence=..., sentence_id=..., game_data=...)
    """
    template = build_prompt(prompt_key)
    try:
        prompt = template.format(**vars)
    except Exception as e:
        print(f"TEMPLATE FORMAT ERROR: {e}")
        raise
    print("PROMPT OK, calling model...")

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
prefix_raw = f"raw_outputs_{model_key}_{prompt_key}_run"
existing = [f for f in os.listdir(raw_outputs_dir) if f.startswith(prefix_raw)]
run_num = len(existing) + 1
raw_outputs_path = os.path.join(raw_outputs_dir, f"{prefix_raw}{run_num}.jsonl")

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

                for ann in parsed.root:
                    start, end = find_token_span_with_context(
                        doc_map=doc_map,
                        target_tokens=ann.TOKENS,
                        left_context=ann.LEFT_CONTEXT,   # FIX 1: was PREFIX
                        right_context=ann.RIGHT_CONTEXT  # FIX 1: was SUFFIX
                    )
                    all_results.append({
                        "TEXT_ID": text_id,
                        "SENTENCE_ID": sent_id,
                        "ANNOTATION_ID": ann.ANNOTATION_ID,
                        "TOKENS": " ".join(ann.TOKENS),
                        "LEFT_CONTEXT": ann.LEFT_CONTEXT,
                        "RIGHT_CONTEXT": ann.RIGHT_CONTEXT,
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
                start, end = find_token_span_with_context(
                    doc_map=doc_map,
                    target_tokens=ann.TOKENS,
                    left_context=ann.LEFT_CONTEXT,   # FIX 1: was PREFIX
                    right_context=ann.RIGHT_CONTEXT  # FIX 1: was SUFFIX
                )
                all_results.append({
                    "TEXT_ID": text_id,
                    "SENTENCE_ID": ann.SENTENCE_ID,
                    "ANNOTATION_ID": ann.ANNOTATION_ID,
                    "TOKENS": " ".join(ann.TOKENS),
                    "LEFT_CONTEXT": ann.LEFT_CONTEXT,
                    "RIGHT_CONTEXT": ann.RIGHT_CONTEXT,
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
prefix_csv = f"results_{model_key}_{prompt_key}_run"
existing_csv = [f for f in os.listdir(csv_dir) if f.startswith(prefix_csv)]
csv_run_num = len(existing_csv) + 1
csv_path = os.path.join(csv_dir, f"{prefix_csv}{csv_run_num}.csv")
df_result.to_csv(csv_path, index=False)

print(f"\nDone in {elapsed}s — {len(df_result)} annotations")
print(f"Raw outputs saved to: {raw_outputs_path}")
print(f"CSV saved to: {csv_path}")