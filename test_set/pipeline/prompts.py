# All prompt templates live here, keyed by short names.
#
# Full-story versions (one LLM call per whole story):
#   p0  - baseline. Shared-task instructions verbatim. Loose output rules.
#   p1  - strict. Same content as p0 but with explicit "JSON only, no preamble" rules.
#   p2  - JSON-context. Recasts the box score as a JSON schema and asks the
#         model to fact-check sentence-by-sentence against it.
#   p3  - persona / "LLM as judge". Casts the model as a senior fact-checker.
#
# Sentence-by-sentence versions are auto-derived at the bottom of this
# file and named p0_sent, p1_sent, p2_sent, p3_sent. They share the body
# of their parent prompt but add a small header telling the model it is
# only being shown one sentence at a time.
#
# Inside each template the curly-brace placeholders are filled in by
# LangChain's PromptTemplate. Doubled braces {{ }} are literal braces
# (used in p2's JSON schema example).

PROMPTS = {
    
    "p0": """Finding Mistakes in Basketball Stories: Text {text_id}

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

"""
,

    "p1": """Finding Mistakes in Basketball Stories: Text {text_id}

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

==================== OUTPUT INSTRUCTIONS ====================

Return a JSON list. Each object must contain EXACTLY these fields:
TEXT_ID, SENTENCE_ID, ANNOTATION_ID, TOKENS, TYPE, CORRECTION, COMMENT

------- TOKENS FIELD (most important — strictly follow) -------

1. TOKENS is a LIST of word strings.
2. TOKENS must be a SHORT span of 1 to 5 consecutive words. Never more than 5.
3. TOKENS must mark ONLY the specific incorrect word(s) — NEVER the full sentence and NEVER the surrounding correct words.
4. TOKENS must be COPIED EXACTLY from the STORY — same spelling, same capitalization, same punctuation. Do not normalize, do not lowercase, do not strip punctuation.
5. The words in TOKENS must appear CONSECUTIVELY in the story, in the same order. Never combine words from different sentences. Never combine stats that appear in different parts of the story.
6. If a sentence contains multiple mistakes, create a SEPARATE annotation object for each mistake. Do not merge them.
7. Each entry in TOKENS must be a single word — never put a multi-word phrase as one string in the list.

------- OTHER FIELDS -------

- TEXT_ID: must be "{text_id}"
- SENTENCE_ID: integer, the 1-indexed sentence number containing the mistake
- ANNOTATION_ID: integer, sequential per document starting from 1
- TYPE: must be EXACTLY one of: NAME, NUMBER, WORD, CONTEXT, NOT_CHECKABLE, OTHER. Use the priority order: NUMBER > NAME > WORD > CONTEXT > NOT_CHECKABLE > OTHER.
- CORRECTION: short string with what the box score actually says
- COMMENT: one short sentence explaining why this is a mistake

------- OUTPUT FORMAT -------

- Output ONLY the JSON list — nothing else.
- No preamble. No "Here are the mistakes:". No markdown code fences. No explanation.
- Do NOT include token position numbers, character offsets, or indices anywhere.
- If you find no mistakes, output an empty list: [].
""",

    
   
     "p2": """You are a basketball fact-checker. Your task is to verify an AI-generated game summary against official box score data provided in structured JSON format.
 
The JSON is your ONLY source of truth. Do not rely on prior knowledge about teams or players.
 
=== BOX SCORE DATA (JSON) ===
{game_data}
 
=== STORY TO FACT-CHECK ===
Text ID: {text_id}
{story}
 
=== HOW TO CHECK ===
Read the story one sentence at a time. For every factual claim, locate the matching field in the JSON above and compare the values.
 
The JSON is structured like this:
{{
  "home_team": "...",
  "away_team": "...",
  "home_pts": 0,
  "away_pts": 0,
  "date": "...",
  "players": [
    {{
      "name": "...",
      "team": "...",
      "pts": 0,
      "reb": 0,
      "ast": 0,
      "starter": true
    }}
  ],
  "line_score": {{
    "home": [0, 0, 0, 0],
    "away": [0, 0, 0, 0]
  }}
}}
 
For each sentence, ask:
- Does it mention a number? → Find the matching JSON field and check the value
- Does it mention a player or team name? → Check it exists in the JSON with that spelling
- Does it describe a result (win/loss, lead, margin)? → Calculate from JSON scores and verify
- Does it say a player started or came off the bench? → Check the "starter" field in JSON
- Does it reference a previous or upcoming game? → Mark as NOT_CHECKABLE if unverifiable
 
=== ERROR TYPE PRIORITY ===
NUMBER > NAME > WORD > CONTEXT > NOT_CHECKABLE > OTHER
 
- NUMBER: wrong numerical value (digits or written words like "six", "third")
- NAME: wrong proper noun — player, team, city, stadium, day of week
- WORD: wrong descriptive word not covered by NAME or NUMBER (e.g. "off the bench" for a starter)
- CONTEXT: literally true but misleading due to surrounding context
- NOT_CHECKABLE: cannot be verified from the box score data
- OTHER: clearly wrong but fits no category above
 
=== OUTPUT FORMAT ===
{format_instructions}
 
Return one object per mistake with EXACTLY these fields:
 
- TEXT_ID: "{text_id}"
- SENTENCE_ID: integer, 1-indexed sentence number in the story
- ANNOTATION_ID: integer, sequential starting from 1
- TOKENS: list of 1 to 5 consecutive words copied EXACTLY from the story — only the wrong words, never the full sentence
- TYPE: one of NAME, NUMBER, WORD, CONTEXT, NOT_CHECKABLE, OTHER
- CORRECTION: the correct value taken directly from the JSON
- COMMENT: one short sentence explaining what the JSON says vs what the story says
 
TOKENS rules:
- Copy words verbatim — same spelling, same capitalisation, same punctuation
- Never combine words from different sentences
- If a sentence has multiple mistakes, create a SEPARATE object for each one
- Each element in the list is a single word — never a multi-word phrase as one string
 
Output ONLY the JSON list. No preamble. No explanation. No markdown code fences.
If you find no mistakes, output: []
""",

    
    
    
    "p3": """
     You are a senior sports journalism fact-checker with an IQ of 165 and 20 years of 
    experience verifying NBA game reports for major outlets like ESPN, The Athletic, and Sports 
    Illustrated. You have personally fact-checked over 15,000 basketball game summaries. Your 
    reputation depends on catching every factual error; wrong scores, wrong names, wrong dates,
    misleading context, while never flagging something that is actually correct. 
    you are known for being precise, methodical, and skeptical.

Your task: review the AI-generated basketball game summary below and flag every factual 
mistake by comparing it against the official box score data. Apply the same rigor you would 
use for a published article.

When you identify a mistake, you mark only the specific incorrect word(s) never the entire 
sentence, never multiple stats from different parts of the story combined together. 
You know that a good fact-checker is surgical, not broad.

For each mistake, classify the type using this priority order:
NUMBER > NAME > WORD > CONTEXT > NOT_CHECKABLE > OTHER

Mistake type definitions:
- NUMBER: wrong numerical value (digits or written words like "six")
- NAME: wrong proper noun — player, team, city, stadium, day of week
- WORD: wrong descriptive word or phrase that is not a name or number (e.g. "off the bench" for a starter)
- CONTEXT: literally true but misleading because of surrounding context
- NOT_CHECKABLE: claim cannot be verified from the box score
- OTHER: clearly wrong but doesn't fit any category above

Main box score data:
{game_data}

STORY:
{story}

TEXT_ID: {text_id}

Now, methodically scan the story sentence by sentence. For each mistake you find, output a JSON object with:
- TEXT_ID
- SENTENCE_ID (1-indexed sentence number)
- ANNOTATION_ID (sequential: 1, 2, 3, ...)
- TOKENS (a list of 1-5 consecutive words copied EXACTLY from the story — only the wrong words, not the full sentence)
- TYPE (one of NAME, NUMBER, WORD, CONTEXT, NOT_CHECKABLE, OTHER)
- CORRECTION (what the box score actually says)
- COMMENT (one short sentence explaining the error)

{format_instructions}

Critical output rules:
- Output ONLY the final JSON list : no preamble, no commentary, no "Here are the mistakes"
- TOKENS must appear as consecutive words in the story and never combine words from different sentences
- Match capitalization, punctuation, and spacing exactly as in the story
- One annotation per mistake : if a sentence has multiple mistakes, create separate annotations
""",
 
   "p4": """
You are a fact-checker for AI-generated basketball game summaries.

You will be given:
1. A basketball game summary (STORY)
2. The real box score data (GAME DATA)

Your job is to find factual errors in the STORY by comparing it against the GAME DATA.

For each error you find, return a JSON object with these exact fields:

- SENTENCE_ID: the sentence number (starting from 1) in the STORY where the error appears.
  Count sentences by splitting on ".", "!" or "?". The first sentence is 1.

- TOKENS: a JSON array of the exact wrong word(s), copied verbatim from the story,
  as individual whitespace-separated items.
  Example: if the error is "Stephen Curry", write ["Stephen", "Curry"]
  Example: if the error is "28", write ["28"]
  Example: if the error is "three-point", write ["three-point"]
  Do NOT write a plain string. Always use a JSON array, even for a single word.

- TYPE: one of NAME, NUMBER, WORD, CONTEXT, NOT_CHECKABLE, OTHER

- CORRECTION: what the correct value should be, as a plain string

- COMMENT: one sentence explaining why it is wrong

- LEFT_CONTEXT: the 2 whitespace-separated tokens that appear immediately BEFORE
  the error in the story, copied character-for-character including any attached
  punctuation. Example: if the story reads "...scored 28 points..." and "28" is
  the error, LEFT_CONTEXT is "scored". If 2 tokens are available write both,
  e.g. "he scored". If the error is at the very start of the story, use "".

- RIGHT_CONTEXT: the 2 whitespace-separated tokens that appear immediately AFTER
  the error in the story, copied character-for-character including any attached
  punctuation. Example: for "...scored 28 points in..." RIGHT_CONTEXT is
  "points in". If the error is at the very end of the story, use "".

Rules:
- TOKENS must be copied character-for-character from the story. Do NOT paraphrase,
  correct, lowercase, or alter them in any way.
- LEFT_CONTEXT and RIGHT_CONTEXT must also be copied exactly from the story,
  character-for-character. Do not alter capitalisation or punctuation.
- Hyphenated words such as "three-point" or "go-ahead" count as ONE token.
  Do not split them.
- Contractions such as "didn't" or "he's" count as ONE token. Do not split them.
- SENTENCE_ID must be an integer. Do NOT leave it null or omit it.
- Do NOT include any numeric token positions or indices.
- Do NOT report the same error twice. Each factual error must appear exactly once.
- Do NOT add any explanation, preamble, or text outside the JSON array.
- Output ONLY a valid JSON array of objects. If you find no errors, output [].

TEXT_ID: {text_id}

GAME DATA:
{game_data}

STORY:
{story}

Return your answer as a JSON array. Each element must look exactly like this (an example):
[
  {{
    "TEXT_ID": "S001",
    "SENTENCE_ID": 2,
    "ANNOTATION_ID": 1,
    "TOKENS": ["28"],
    "TYPE": "NUMBER",
    "CORRECTION": "24",
    "COMMENT": "Box score shows 24 points, not 28.",
    "LEFT_CONTEXT": "scored",
    "RIGHT_CONTEXT": "points in"
  }}
]

If you find no errors, return exactly: []
Return ONLY the JSON array. No schema. No explanation. Nothing else.
""",
}


# p0a = p0 plus a tail (per Craig, Jun 2026) that spells out exactly which
# tokens to record in the TOKENS field for each mistake category. TOKENS is
# the key our schema uses for the wrong word(s) the model copies from the story.
_P0A_TAIL = """

For each error, include as the TOKENS annotation only the sequential span of tokens of the given category.

For example;

If the mistake is that a named entity is incorrect, then the category is NAME and only the token(s) matching that single named entity should be included, e.g., "LeBron James", "Dallas Mavericks", "Monday", etc.

If the mistake is that a numeric value is incorrect, then the category is NUMBER and only the token(s) that are inaccurate numbers should be included, e.g., "1", "two", "3 - point", etc.

If the mistake is that any other word or phrase is incorrect, then the category is WORD, and only the token(s) that are part of the inaccurate word or phrase should be included, e.g., "on the road", "return home".

Any fact in the text that cannot be verified against the data tables should be marked as NOT_CHECKABLE, following the token inclusion rules as if it were a NAME, NUMBER, or WORD error.
"""

PROMPTS["p0a"] = PROMPTS["p0"] + _P0A_TAIL


# Build the sentence-by-sentence variants programmatically. Each one is
# the full-story prompt with two tweaks:
#   1. A short header is prepended that tells the model it is seeing
#      one sentence and locks the SENTENCE_ID it should report.
#   2. The {story} placeholder is renamed to {sentence}, because the
#      caller will now pass a single sentence rather than the full text.
_SENT_HEADER = (
    "MODE: SENTENCE-BY-SENTENCE\n"
    "You are given ONE sentence (sentence_id={sentence_id}) from a basketball game story.\n"
    "Fact-check ONLY this sentence against the box-score data below.\n"
    "If this sentence has no mistakes, output [].\n"
    "Always set SENTENCE_ID = {sentence_id} in every annotation you return.\n"
    "TOKENS must be copied EXACTLY from this sentence (not from any other text).\n\n"
)

for _k in ["p0", "p0a", "p1", "p2", "p3"]:
    PROMPTS[_k + "_sent"] = _SENT_HEADER + PROMPTS[_k].replace("{story}", "{sentence}")
