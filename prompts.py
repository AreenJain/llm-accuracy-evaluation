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

Return a LIST of objects.

Each object must contain:
TEXT_ID, SENTENCE_ID, ANNOTATION_ID, TOKENS, TYPE, CORRECTION, COMMENT

CRITICAL RULES for TOKENS field:
- TOKENS must be a SHORT span of 1 to 5 consecutive words copied EXACTLY from the story
- TOKENS must mark ONLY the specific incorrect word(s) — NOT the entire sentence
- TOKENS must appear together consecutively in the story — DO NOT combine words from different sentences or different parts of the story
- Match exact capitalization, punctuation, and spacing as in the story
- If a sentence has multiple mistakes, create a SEPARATE annotation for each mistake

Other rules:
- Output ONLY JSON (no preamble, no explanation)
- Do NOT include token positions
- TYPE must be one of: NAME, NUMBER, WORD, CONTEXT, NOT_CHECKABLE, OTHER""",

    "p2": """[P1 + few-shot examples]""",

    "p3": """[P2 + chain-of-thought]""",

    "p4": """[Minimal stripped-down prompt]""",
}