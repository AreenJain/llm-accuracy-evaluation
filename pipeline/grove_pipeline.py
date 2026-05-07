import re
import time
import argparse
import pandas as pd
from typing import List, Optional
from pydantic import BaseModel, RootModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# CLI
arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--games", type=str, required=True)
arg_parser.add_argument("--jsonl", type=str, required=True)
arg_parser.add_argument("--model", type=str, default="llama_medium")
arg_parser.add_argument("--rows", type=int, default=20)
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

def build_prompt():
    return PromptTemplate(
        template="""Finding Mistakes in Basketball Stories: Text {text_id}

In this document you will find:
Our guidelines on pages 2-5.
An example basketball story which we have marked up on pages 6 and 7.
The story we would like you to mark up, on page 8.  We give links to basketball-reference.com for the box score information as well as the season schedule for each team (such that you can find other games which might be mentioned in the text).  We also include a link to an online calendar for the month the game was played in.
Space for any additional comments you may have on page 9 (you can leave any optional feedback here, or on the Mechanical Turk form, whichever is easier).
Participant Information Sheet, along with contact information for the researchers on page 10.
Please mark up the game summary on page 8 in a similar way to the example on pages 6/7 and upload the document as instructed on Mechanical Turk.
Thanks for your help!

Mark-up guidelines
We've given you a basketball game story produced by a "deep learning" AI system, as well as links to box score information on basketball-reference.com about the game (the stories focus on box scores, they generally don't talk about individual goals, penalties, etc).  We have also given links for season information of each team (some of the stories say where the next game will be).
We are only interested in whether the presented statements/facts are correct, not whether they are boring and should have been replaced by more interesting statements/facts.  We are not interested in spelling or grammar mistakes.
Please read through the stories and mark up cases where:
numbers are wrong
names (players, teams, cities, days of the week, etc) are wrong
words are wrong
context means people will misunderstand a sentence
facts are not checkable
other cases where the story says something which is not true
We give more information below about these types of mistake.
Please mark up the wrong numbers, names, etc by putting them in red.  If you're colour-blind, you can underline them instead.   Also please add a note below the story for each mistake; the note should explain the mistake and say which type it is.  There is an example on pages 6 and 7.
Number mistakes
Numbers mistakes are incorrect numbers.  For example
"10-point victory" when margin of victory was 11 pts.
"six players reached double figures" when only four players did so.
Please mark-up the wrong number by putting it in red or underlining it.  It doesn't matter whether the number is digits (such as 10) or written as a word (such as six).  Ordinals (1st, 2nd, third etc.) are also number mistakes.
Name mistakes
Name mistakes are errors in things that have names.  This includes people, cities, teams, stadiums, and days of week.   If a word (other than "I") is always capitalised, it is probably a name. For example
"on Monday" when game was played on Wednesday.
"Talking Stick Resort Arena" when game was played in US Airways Arena.
"Isaiah Thomas had 11 points and 3 rebounds" when he had neither of these statistics, and Gerald Green had both.

Please mark-up the wrong name by putting it in red or underlining it.  Please note that days of the week, such as Wednesday, are always name mistakes, not word mistakes.
Word mistakes
Word mistakes are incorrect or inappropriate words which are not names or numbers.  For example
"out-scored the Suns" when the Suns had a higher score in this period.
"off the bench" for a player who was on the starting team.
"strong first half" when team did poorly in first half.
Please mark-up the wrong word(s) by putting it in red or underlining it.   We treat mistakes in fixed phrases such as "off the bench" as word mistakes (the AI systems treat fixed phrases in the same way as they treat words).  Please note that days of the week (Monday, Tuesday etc.) are not word mistakes (they are name mistakes).
Context mistakes
Context mistakes occur when people reading a sentence are likely to misinterpret it because of its context, even if the sentence is literally true.  For example
"The Suns had six players reach double figures in points.  Mike Conley led the way with 24 points."   This is a context mistake because Conley played for the other team (not the Suns).
For the mark-up, try to find the thing which will be misinterpreted (as above), and put it in red or underline it.
Facts which are not checkable
Some facts will not be practical to check.  We do not expect you to look back further than 4 prior games to check a statement.
Other mistakes
If there is a mistake which clearly does not belong to any of the above categories, you may use this category as a last resort.
Complex mistakes
If there are multiple ways in which you can annotate a sentence for mistakes, choose the one with the fewest total mistakes.
Number > Name > Word > Context > Not Checkable > Other.

Main box score data
{game_data}

Other useful data
Home team season schedule: https://www.basketball-reference.com/teams/BOS/2017_games.html
Visiting team season schedule: https://www.basketball-reference.com/teams/LAL/2017_games.html
Online calendar: https://www.timeanddate.com/calendar/monthly.html?year=2017&month=02&country=1

STORY
{story}

LIST OF MISTAKES
<please list mistakes here, as well as marking them up in the story>

{format_instructions}

Return a LIST of objects.

Each object must contain:
TEXT_ID
SENTENCE_ID
ANNOTATION_ID
TOKENS
TYPE
CORRECTION
COMMENT

Rules:
- Output ONLY JSON
- TOKENS must be list of exact words from story
- Do NOT include token positions
- Do NOT explain anything
""",
        input_variables=["text_id", "story", "game_data"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

def extract_json(text):
    if not text:
        return "[]"
    match = re.search(r'\[.*\]', text, re.DOTALL)
    return match.group() if match else "[]"

def build_doc_token_map(text_id, story):
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
    target_len = len(target_tokens)
    for i in range(len(tokens)):
        if tokens[i:i+target_len] == target_tokens:
            return i+1, i+target_len
    return None, None

# Load model
model_key = args.model
model_name = MODELS[model_key]

print(f"Loading {model_name}...")
from transformers import BitsAndBytesConfig

tokenizer = AutoTokenizer.from_pretrained(model_name)

# 4-bit configuration banaya taaki model chota ho jaye
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True
)

llm = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    max_memory={0: "25GiB", 1: "46GiB"},  
    quantization_config=bnb_config
)

print("Model loaded.")

def prompt_fn(text_id, story, game_data):
    template = build_prompt()
    prompt = template.format(text_id=text_id, story=story, game_data=game_data)
    
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(llm.device)
    
    with torch.no_grad():
        outputs = llm.generate(**inputs, max_new_tokens=2048, do_sample=False)
    
    result_text = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    result_text = extract_json(result_text)
    try:
        return parser.parse(result_text)
    except Exception:
        return parser.parse("[]")

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
start_time = time.time()

for i, row in games_df.head(args.rows).iterrows():
    text_id = row["TEXT_ID"]
    story = row["GENERATED_TEXT"]
    game_data = row["game_data"]
    
    print(f"Processing {text_id}...")
    
    try:
        parsed = prompt_fn(text_id, story, game_data)
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
        
    # Agli row process hone se pehle purani memory free kar do
    import gc
    gc.collect()
    torch.cuda.empty_cache()

elapsed = round(time.time() - start_time, 2)
df_result = pd.DataFrame(all_results)
df_result["MODEL"] = model_key
df_result["TIME_SECONDS"] = elapsed
df_result.to_csv(f"results_{model_key}.csv", index=False)
print(f"\nDone in {elapsed}s — {len(df_result)} annotations")