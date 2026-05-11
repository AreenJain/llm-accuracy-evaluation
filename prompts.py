# prompts.py — all prompt variants

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

    
   
    "p2": """[P1 + few-shot examples]""",

    
    
    
    "p3": """You are a senior sports journalism fact-checker with an IQ of 165 and 20 years of 
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
}