"""Banned patterns dictionary and regex rules for AI tells and VC clichés."""

import re
from typing import Dict, Pattern

# Regular expressions targeting Wikipedia's 'Signs of AI writing' and ubiquitous LLM slop
BANNED_PHRASES: Dict[str, str] = {
    # The notorious correlative conjunction AI trope
    r"\bnot\s+(?:only|just)\b.*?\bbut\s+(?:also)?\b": "Correlative conjunction ('not only X, but also Y') is a classic AI tell. State both facts directly.",
    # High-frequency synthetic metaphors
    r"\btestament\s+to\b": "Banned cliché: 'testament to'. Replace with concrete causal evidence.",
    r"\bserves?\s+as\s+a\s+(?:beacon|testament|reminder|catalyst)\b": "Banned cliché: 'serves as a [metaphor]'. State the direct impact.",
    r"\bdelv(?:e|es|ed|ing)\b": "Banned AI word: 'delve'. Use 'analyze', 'examine', or omit.",
    r"\btapestry\b": "Banned AI word: 'tapestry'. Use concrete structural terminology.",
    r"\b(?:ever[- ]evolving|rapidly\s+evolving|shifting)\s+landscape\b": "Banned cliché: 'evolving landscape'. State the exact market transition.",
    r"\bin\s+an\s+increasingly\s+\w+\s+world\b": "Banned cliché: 'in an increasingly [X] world'. Cut throat-clearing opening.",
    r"\bpoised\s+to\b": "Banned passive assertion: 'poised to'. Assert what the company actually does or has done.",
    r"\bwell[- ]positioned\s+to\b": "Banned corporate jargon: 'well-positioned to'. Show the unit economics proving the advantage.",
    r"\bholistic(?:ally)?\b": "Banned buzzword: 'holistic'. Specify the exact integrated components.",
    r"\bpivotal\b": "Overused AI hyperbole: 'pivotal'. Show the data point instead of editorializing.",
    r"\bbeacon\s+of\b": "Banned AI metaphor: 'beacon of'. State the specific standard.",
    r"\bmultifaceted\b": "Banned AI filler: 'multifaceted'. Enumerate the specific factors.",
    r"\bfosters?\b": "Overused AI verb: 'fosters'. Use concrete active verbs.",
    r"\bit\s+is\s+(?:worth\s+noting|important\s+to\s+remember)\b": "Cowardly throat-clearing: 'it is worth noting'. Cut and state the fact directly.",
    r"\bremains\s+to\s+be\s+seen\b": "Banned non-committal cliché: 'remains to be seen'. State the specific falsification metric.",
    r"\bcould\s+potentially\b": "Redundant double-hedging: 'could potentially'. Use 'could' or define the probability.",
}

COMPILED_BANNED_RULES = {
    pattern: (re.compile(pattern, re.IGNORECASE), explanation)
    for pattern, explanation in BANNED_PHRASES.items()
}

# Em-dash pattern: matches either Unicode em-dash (—) or double hyphen (--)
EM_DASH_PATTERN = re.compile(r"—|--")

# Rule-of-three adjective / noun pattern: e.g. "scalable, robust, and reliable"
RULE_OF_THREE_PATTERN = re.compile(
    r"\b([a-zA-Z]+),\s+([a-zA-Z]+),\s+and\s+([a-zA-Z]+)\b",
    re.IGNORECASE,
)
