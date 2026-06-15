import csv
import json
import pprint
import sys
import yaml
from copy import deepcopy
import argparse

# Instantiate the parser
parser = argparse.ArgumentParser(description='Optional app description')

pp = pprint.PrettyPrinter(indent=4)

"""
  It is possible for a metric to present multiple annotations which map to one annotation in the GSML.
     or vice verse.
  For example, "Miami Heat" could be a 2-token error "Miami Heat".
     or two 1-token errors "Miami" (wrong city) "Heat" (wrong name).
  We award correct recall when at least one submitted mistake matches a GSML mistake.
  We award correct precision when a submitted mistake matches at least one GSML mistake.
  Mistakes are said to match when their ranges of token ids overlap.
  Once a submitted mistake has recalled a GSML mistake, the submitted mistake is consumed
    - It cannot recall a subsequent GSML mistake

  Column formats:
  GSML format (gold standard):
    TEXT_ID, SENTENCE_ID, ANNOTATION_ID, TOKENS,
    SENT_TOKEN_START, SENT_TOKEN_END, DOC_TOKEN_START, DOC_TOKEN_END, TYPE, CORRECTION, COMMENT

  LLM results format (submitted):
    TEXT_ID, SENTENCE_ID, ANNOTATION_ID, TOKENS,
    DOC_TOKEN_START, DOC_TOKEN_END, TYPE, CORRECTION, COMMENT, MODEL, TIME_SECONDS
"""

# ---------------------------------------------------------------------------
# Column index maps for each supported format
# ---------------------------------------------------------------------------
# GSML: has both sent-level and doc-level token indices
GSML_COLUMNS = {
  'text_id':        0,
  'sentence_id':    1,
  'annotation_id':  2,
  'tokens':         3,
  'sent_start_idx': 4,   # SENT_TOKEN_START
  'sent_end_idx':   5,   # SENT_TOKEN_END
  'doc_start_idx':  6,   # DOC_TOKEN_START
  'doc_end_idx':    7,   # DOC_TOKEN_END
  'category':       8,   # TYPE
}

# LLM results: no sent-level indices
LLM_COLUMNS = {
  'text_id':        0,
  'sentence_id':    1,
  'annotation_id':  2,
  'tokens':         3,
  'sent_start_idx': None,  # not present
  'sent_end_idx':   None,  # not present
  'doc_start_idx':  4,   # DOC_TOKEN_START
  'doc_end_idx':    5,   # DOC_TOKEN_END
  'category':       6,   # TYPE
}

FORMAT_MAP = {
  'gsml': GSML_COLUMNS,
  'llm':  LLM_COLUMNS,
}

''' Returns the category labels described in the paper '''
def all_categories():
  return ['NAME', 'NUMBER', 'WORD', 'CONTEXT', 'NOT_CHECKABLE', 'OTHER']

''' Returns an int or None '''
def csv_int(x):
  return int(float(x)) if x else None

''' Helper that checks that either DOC or SENT based tokenization is used throughout'''
def consistent_tokenization(tokenization_mode, current_line_mode):
  if tokenization_mode not in {None, current_line_mode}:
    raise Exception('You must consistently use either document-based, sentence-based or both for the tokenization method.')
  return current_line_mode

"""
  Creates and returns a dictionary representation of the mistake list (GSML or Submission).

  file_format: 'gsml' (default) or 'llm'
    - 'gsml' expects the classic WebAnno export with both SENT and DOC token indices.
    - 'llm'  expects the new LLM results format with DOC-only indices and TYPE in col 6.

  The dictionary is structured as:
    { TEXT_ID: { DOC_START_IDX: mistake_data, ... }, ... }

  Returns (mistake_dict, num_mistakes).
"""
def create_mistake_dict(filename, categories, token_lookup, file_format='gsml'):
  cols = FORMAT_MAP.get(file_format)
  if cols is None:
    raise ValueError(f"Unknown file_format '{file_format}'. Choose 'gsml' or 'llm'.")

  mistake_dict = {}
  tokens_used = {}
  with open(filename, newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    next(reader, None)  # skip header

    num_mistakes = 0
    tokenization_mode = None

    for i, row in enumerate(reader):
      # --- read columns using the format-specific index map ---
      text_id        = row[cols['text_id']].replace('.txt', '')
      sentence_id    = csv_int(row[cols['sentence_id']])
      annotation_id  = csv_int(row[cols['annotation_id']])
      tokens         = row[cols['tokens']]
      category       = row[cols['category']]

      # Sentence-level indices (may be absent in LLM format)
      sent_start_idx = csv_int(row[cols['sent_start_idx']]) if cols['sent_start_idx'] is not None else None
      sent_end_idx   = csv_int(row[cols['sent_end_idx']])   if cols['sent_end_idx']   is not None else None

      # Doc-level indices
      doc_start_idx  = csv_int(row[cols['doc_start_idx']])
      doc_end_idx    = csv_int(row[cols['doc_end_idx']])

      # --- resolve tokenization ---
      sent_given = (sent_start_idx is not None and sent_end_idx is not None and sentence_id is not None)
      doc_given  = (doc_start_idx  is not None and doc_end_idx  is not None)

      if sent_given and doc_given:
        tokenization_mode = consistent_tokenization(tokenization_mode, 'BOTH')
        # Verify cross-mapping against token_lookup
        assert doc_start_idx == token_lookup['sent_to_doc'][text_id][sentence_id][sent_start_idx]
        assert doc_end_idx   == token_lookup['sent_to_doc'][text_id][sentence_id][sent_end_idx]
        assert sentence_id   == token_lookup['doc_to_sent'][text_id][doc_start_idx]['sentence_id']
        assert sent_start_idx == token_lookup['doc_to_sent'][text_id][doc_start_idx]['token_id']
        assert sent_end_idx   == token_lookup['doc_to_sent'][text_id][doc_end_idx]['token_id']
      elif sent_given:
        tokenization_mode = consistent_tokenization(tokenization_mode, 'SENT')
        doc_start_idx = token_lookup['sent_to_doc'][text_id][sentence_id][sent_start_idx]
        doc_end_idx   = token_lookup['sent_to_doc'][text_id][sentence_id][sent_end_idx]
      elif doc_given:
        tokenization_mode = consistent_tokenization(tokenization_mode, 'DOC')
        sentence_id    = token_lookup['doc_to_sent'][text_id][doc_start_idx]['sentence_id']
        sent_start_idx = token_lookup['doc_to_sent'][text_id][doc_start_idx]['token_id']
        sent_end_idx   = token_lookup['doc_to_sent'][text_id][doc_end_idx]['token_id']
      else:
        raise Exception(
          f'You must provide either document or sentence based token ids on {filename} row {i}'
        )

      # --- filter by category ---
      if category not in categories:
        continue

      # --- duplicate / overlapping span check ---
      if text_id not in tokens_used:
        tokens_used[text_id] = set()

      for x in range(doc_start_idx, doc_end_idx + 1):
        if x in tokens_used[text_id]:
          raise Exception(f'Token {x} already used, duplicate on {text_id}:{i}')
        tokens_used[text_id].add(x)

      # --- store mistake ---
      if text_id not in mistake_dict:
        mistake_dict[text_id] = {}

      mistake_dict[text_id][doc_start_idx] = {
        'set':            set(range(doc_start_idx, doc_end_idx + 1)),
        'category':       category,
        'sent_start_idx': sent_start_idx,
        'sent_end_idx':   sent_end_idx,
        'doc_start_idx':  doc_start_idx,
        'doc_end_idx':    doc_end_idx,
        'sentence_id':    sentence_id,
        'annotation_id':  annotation_id,
        'tokens':         tokens,
      }
      num_mistakes += 1

  return mistake_dict, num_mistakes


"""
  Recall is when at least one submitted mistake overlaps the GSML mistake
  - once a submitted mistake has been used for correct recall, it cannot be used again (it is consumed).
  Precision is when a submitted mistake overlaps any GSML mistake.
"""
def match_mistake_dicts(gsml, submitted):
  per_category_matches = {k: {} for k in all_categories()}

  # Copy this because the algorithm consumes elements
  copy_submitted = deepcopy(submitted)

  for text_id, gsml_text_data in gsml.items():
    for doc_start_idx, gsml_error_data in gsml_text_data.items():
      category = gsml_error_data['category']
      assert category in per_category_matches

      pop_key = None
      if text_id in copy_submitted:
        for submitted_doc_start_idx, submitted_error_data in copy_submitted[text_id].items():
          if submitted_error_data['set'].intersection(gsml_error_data['set']):
            pop_key = submitted_doc_start_idx
            break

      match = pop_key is not None
      if match:
        copy_submitted[text_id].pop(pop_key, None)

      per_category_matches[category][f'{text_id}_{doc_start_idx}'] = match

  return per_category_matches


'''Returns the correct and incorrect recall totals'''
def get_recall(matches):
  correct   = {k: 0 for k in all_categories()}
  incorrect = {k: 0 for k in all_categories()}
  for category, h in matches.items():
    for _, v in h.items():
      if v:
        correct[category]   += 1
      else:
        incorrect[category] += 1
  return correct, incorrect


def get_document_tokens(token_lookup):
  document_tokens = {}
  for text_id, token_data in token_lookup['doc_to_sent'].items():
    document_tokens[text_id] = {}
    for doc_token_id in token_data.keys():
      document_tokens[text_id][doc_token_id] = {
        'gsml':      False,
        'submitted': False,
      }
  return document_tokens


def match_tokens(data, document_tokens, mode):
  for text_id, text_data in data.items():
    for _, error_data in text_data.items():
      for x in range(error_data['doc_start_idx'], error_data['doc_end_idx'] + 1):
        document_tokens[text_id][x][mode] = True


def get_token_level_result(gsml, submitted, token_lookup):
  document_tokens = get_document_tokens(token_lookup)
  match_tokens(gsml,      document_tokens, 'gsml')
  match_tokens(submitted, document_tokens, 'submitted')

  recall = recall_denominator = precision_denominator = 0

  for text_id, data in document_tokens.items():
    for _, v in data.items():
      if v['gsml'] and v['submitted']:
        recall += 1
      if v['gsml']:
        recall_denominator += 1
      if v['submitted']:
        precision_denominator += 1

  return {
    'recall':                recall,
    'recall_denominator':    recall_denominator,
    'precision_denominator': precision_denominator,
  }


def safe_divide(x, y):
  return x / y if y > 0 else None


"""
  checks that the token text in the submission matches that retrieved by DOCUMENT-level IDs
"""
def check_token_ids(mistake_dict, text_dir):
  for text_id, text_errors in mistake_dict.items():
    with open(f'{text_dir}/{text_id}.txt', 'r') as fh:
      raw_tokens = fh.read().split()
      for doc_start_idx, h in text_errors.items():
        assert doc_start_idx == h['doc_start_idx']
        for i, t in enumerate(h['tokens'].split()):
          # Token IDs start at 1 (WebAnno convention)
          assert raw_tokens[doc_start_idx + i - 1] == t


"""
  Returns a dict containing sub-dicts of recall, precision and overlaps
  between a GSML file and a submission file.

  submitted_format: 'gsml' or 'llm' — controls which column layout is used
    for the submitted file. The GSML gold file always uses 'gsml' format.
"""
def calculate_recall_and_precision(
    gsml_filename, submitted_filename, token_lookup, text_dir,
    categories=[], submitted_format='llm'
):
  gsml,      gsml_num_lines      = create_mistake_dict(gsml_filename,      categories, token_lookup, file_format='gsml')
  submitted, submitted_num_lines = create_mistake_dict(submitted_filename, categories, token_lookup, file_format=submitted_format)

  if text_dir is not None:
    print('\tChecking GSML for token match against raw texts:')
    check_token_ids(gsml, text_dir)
    print('\tChecking Submitted for token match against raw texts:')
    check_token_ids(submitted, text_dir)

  # Mistake level
  per_category_matches = match_mistake_dicts(gsml, submitted)
  correct_recall_h, incorrect_recall_h = get_recall(per_category_matches)
  correct_recall   = sum(correct_recall_h.values())
  incorrect_recall = sum(incorrect_recall_h.values())

  assert (correct_recall + incorrect_recall) == gsml_num_lines

  recall    = safe_divide(correct_recall, gsml_num_lines)
  precision = safe_divide(correct_recall, submitted_num_lines)

  # Token level
  token_result      = get_token_level_result(gsml, submitted, token_lookup)
  token_recall      = safe_divide(token_result['recall'], token_result['recall_denominator'])
  token_precision   = safe_divide(token_result['recall'], token_result['precision_denominator'])

  return {
    'recall': {
      'value':    recall,
      'correct':  correct_recall,
      'of_total': gsml_num_lines,
    },
    'precision': {
      'value':    precision,
      'correct':  correct_recall,
      'of_total': submitted_num_lines,
    },
    'token_recall': {
      'value':    token_recall,
      'correct':  token_result['recall'],
      'of_total': token_result['recall_denominator'],
    },
    'token_precision': {
      'value':    token_precision,
      'correct':  token_result['recall'],
      'of_total': token_result['precision_denominator'],
    },
    'correct_recall_debug':   correct_recall_h,
    'incorrect_recall_debug': incorrect_recall_h,
  }


def format_result_value(value, dcp=3):
  return round(value, dcp) if value is not None else None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
parser.add_argument('--gsml',         type=str, help='The GSML file path (CSV)')
parser.add_argument('--submitted',    type=str, nargs='?', help='The submitted file path (CSV)')
parser.add_argument('--token_lookup', type=str, help='The tokenization file (YAML)')
parser.add_argument('--text_dir',     type=str, help='The directory where the raw texts are')
parser.add_argument('--csv_out',      type=str, help='Path to an output CSV file for stats (optional)')
parser.add_argument(
  '--submitted_format', type=str, default='llm', choices=['gsml', 'llm'],
  help=(
    "Column layout of the submitted CSV. "
    "'llm'  = new LLM results format: TEXT_ID,SENTENCE_ID,ANNOTATION_ID,TOKENS,DOC_TOKEN_START,DOC_TOKEN_END,TYPE,... (default). "
    "'gsml' = classic WebAnno format: ...,SENT_TOKEN_START,SENT_TOKEN_END,DOC_TOKEN_START,DOC_TOKEN_END,TYPE."
  )
)

args = parser.parse_args()
gsml_filename      = args.gsml
submitted_filename = args.submitted
token_lookup_filename = args.token_lookup
text_dir           = args.text_dir
csv_out            = args.csv_out
submitted_format   = args.submitted_format

with open(token_lookup_filename, 'r') as fh:
  token_lookup = yaml.full_load(fh)

print('\n\n')
print('-' * 80)
print('GSML: EVALUATE')
print(f'comparing GSML => "{gsml_filename}" to submission => "{submitted_filename}"')
print(f'submitted format: {submitted_format}')

categories_list = [all_categories()] + [[x] for x in all_categories()]
csv_lines = [[
  'categories', 'recall', 'precision', 'token_recall', 'token_precision',
  'submitted_filename', 'gsml_filename', 'token_lookup_filename', 'text_dir',
]]

for categories in categories_list:
  category_display_str = ', '.join(categories)
  print('\n\n--------------------------------------------')
  print(f'-- GSML for categories: [{category_display_str}]')

  result = calculate_recall_and_precision(
    gsml_filename, submitted_filename, token_lookup, text_dir,
    categories, submitted_format=submitted_format
  )
  recall         = format_result_value(result['recall']['value'])
  precision      = format_result_value(result['precision']['value'])
  token_recall   = format_result_value(result['token_recall']['value'])
  token_precision = format_result_value(result['token_precision']['value'])

  csv_lines.append([
    '|'.join(categories),
    str(recall), str(precision), str(token_recall), str(token_precision),
    submitted_filename, gsml_filename, text_dir,
  ])

  print(f'\tsummary: recall => {recall}, precision => {precision}, token_recall => {token_recall}, token_precision => {token_precision}')
  print('\tbreakdown:')
  for k, v in result.items():
    print(f'\t\t{k}')
    for sub_k, sub_v in v.items():
      print(f'\t\t\t{sub_k} => {sub_v}')

if csv_out is not None:
  with open(csv_out, 'w') as fh:
    s = '\n'.join([','.join(arr) for arr in csv_lines])
    fh.write(f'{s}\n')