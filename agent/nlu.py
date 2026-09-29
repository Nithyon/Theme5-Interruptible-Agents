"""Rule-based language understanding.

Extracts typed values (places, dates, times, names, numbers, codes) from text,
matches a request to manifest tools using only their names and descriptions,
and classifies interruptions. Nothing here knows scenario-specific cities,
tools or phrasings; it works from general English cues and the manifest.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december")
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "twenty": 20, "thirty": 30,
    "a couple of": 2, "a couple": 2, "a pair of": 2, "single": 1, "double": 2,
}

# Capitalised words that start sentences or fill speech, never place or person names.
_NOT_NAMES = {
    "i", "i'm", "i'd", "i'll", "a", "an", "the", "please", "can", "could", "would", "will",
    "wait", "hey", "hi", "hello", "ok", "okay", "so", "and", "but", "or", "actually", "sorry",
    "what", "what's", "whats", "where", "when", "how", "why", "who", "which", "find", "book",
    "show", "get", "tell", "give", "make", "change", "switch", "cancel", "yes", "yeah", "no",
    "nope", "um", "uh", "hmm", "oh", "well", "also", "just", "let", "let's", "is", "are",
    "do", "does", "my", "me", "it", "this", "that", "there", "here", "am", "pm", "a.m.",
    "p.m.", "not", "never", "forget", "thanks", "thank", "great", "cool", "sure", "right",
    "now", "today", "tomorrow", "tonight", "next", "last", "this", "search", "look",
}
_NOT_NAMES.update(WEEKDAYS)
_NOT_NAMES.update(MONTHS)

_CAP_WORD = r"(?:[A-Z][a-zA-Z'\.\-]*[a-zA-Z]|[A-Z])"
_CAP_SEQ = rf"{_CAP_WORD}(?:\s+{_CAP_WORD})*"

STOPWORDS = {
    "a", "an", "the", "to", "for", "in", "on", "at", "of", "me", "my", "i", "you", "your",
    "can", "could", "would", "please", "what", "whats", "is", "are", "be", "like", "it",
    "this", "that", "and", "or", "with", "do", "does", "how", "some", "any", "want", "need",
    "there", "here", "right", "now", "wait", "actually", "hey", "hi", "just", "also", "im",
    "will", "we", "us", "our", "from", "by", "about", "one", "get", "going", "go", "if",
    "tell", "give", "let", "lets", "should", "so", "up", "out", "am", "pm",
}

# General verb/noun equivalences between how people talk and how tools are named.
SYNONYMS = {
    "find": "search", "look": "search", "lookup": "search", "check": "search",
    "show": "search", "list": "search", "fly": "flight", "plane": "flight",
    "airfare": "flight", "reserve": "book", "reservation": "book", "much": "quote",
    "cost": "quote", "price": "quote", "rate": "quote", "estimate": "quote",
    "temperature": "weather", "forecast": "weather", "rain": "weather",
    "open": "create", "file": "create", "raise": "create", "submit": "create",
    "log": "create", "report": "create", "manual": "manual",
    "guide": "manual", "instructions": "manual", "troubleshoot": "manual",
    "fix": "manual", "broken": "manual", "error": "manual", "blink": "manual",
    "stay": "hotel", "room": "hotel", "rental": "rental", "rent": "rental",
}


# ---------------------------------------------------------------------------
# tokens
# ---------------------------------------------------------------------------
def stem(word: str) -> str:
    w = word.lower().strip("'")
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("ing") and len(w) > 5:
        w = w[:-3]
        if len(w) > 2 and w[-1] == w[-2]:
            w = w[:-1]
        return w
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z']*|\d+", text or "")


def content_stems(text: str) -> List[str]:
    out = []
    for w in words(text):
        lw = w.lower().replace("'", "")
        if lw in STOPWORDS:
            continue
        s = stem(lw)
        out.append(s)
        if lw in SYNONYMS:
            out.append(SYNONYMS[lw])
        elif s in SYNONYMS:
            out.append(SYNONYMS[s])
    return out


def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(phrase.lower()) + r"(?![a-z])",
                     (text or "").lower()) is not None


# ---------------------------------------------------------------------------
# typed value extraction
# ---------------------------------------------------------------------------
def _clean_name(seq: str) -> Optional[str]:
    parts = seq.strip().rstrip(".,!?;:").split()
    while parts and parts[0].lower().rstrip(".,") in _NOT_NAMES:
        parts.pop(0)
    while parts and parts[-1].lower().rstrip(".,") in _NOT_NAMES:
        parts.pop()
    if not parts:
        return None
    name = " ".join(p.rstrip(".,!?;:") for p in parts)
    return name or None


def extract_locations(text: str) -> List[Tuple[str, str]]:
    """Return [(preposition, place)] in order of appearance."""
    found: List[Tuple[int, str, str]] = []
    pattern = re.compile(
        r"\b(to|in|at|from|near|around|into|towards?|via|over)\s+(?:the\s+)?(" + _CAP_SEQ + r")")
    for m in pattern.finditer(text or ""):
        name = _clean_name(m.group(2))
        if name:
            found.append((m.start(), m.group(1).lower(), name))
    correction = re.compile(
        r"\b(?:make\s+it|change\s+(?:it\s+)?to|switch\s+(?:it\s+)?to|go\s+with|i\s+meant"
        r"|i\s+said|how\s+about|what\s+about|let'?s\s+(?:do|try)|instead\s+of|rather\s+than"
        r"|not)\s+(" + _CAP_SEQ + r")")
    for m in correction.finditer(text or ""):
        name = _clean_name(m.group(1))
        if name and not any(name == f[2] for f in found):
            found.append((m.start(), "make", name))
    trailing = re.compile(r"(" + _CAP_SEQ + r")\s+instead\b")
    for m in trailing.finditer(text or ""):
        name = _clean_name(m.group(1))
        if name and not any(name == f[2] for f in found):
            found.append((m.start(), "make", name))
    found.sort()
    out = []
    for _, prep, name in found:
        if extract_date(name) or extract_time(name):
            continue
        out.append((prep, name))
    return out


def negated_values(text: str) -> List[str]:
    """Values the user explicitly rejects ("not Boston", "instead of Boston")."""
    out = []
    for m in re.finditer(r"\b(?:not|instead\s+of|rather\s+than)\s+(" + _CAP_SEQ + r")", text or ""):
        name = _clean_name(m.group(1))
        if name:
            out.append(name)
    return out


def pick_location(text: str, role: str = "any") -> Optional[str]:
    locs = extract_locations(text)
    if not locs:
        return None
    rejected = {n.lower() for n in negated_values(text)}
    locs = [(p, n) for p, n in locs if n.lower() not in rejected] or locs
    preferred = {
        "destination": ("to", "make", "into", "towards", "toward", "in", "at"),
        "origin": ("from", "via"),
        "pickup": ("in", "at", "from", "make", "near"),
        "any": ("make", "to", "in", "at", "near", "around", "from"),
    }.get(role, ("make", "to", "in", "at"))
    corrections = [n for p, n in locs if p == "make"]
    if corrections:
        return corrections[-1]
    for prep in preferred:
        for p, n in reversed(locs):
            if p == prep:
                return n
    return locs[-1][1]


def extract_date(text: str) -> Optional[str]:
    t = text or ""
    pats = [
        r"\bday\s+after\s+tomorrow\b",
        r"\b(?:tomorrow|today|tonight)(?:\s+(?:morning|afternoon|evening|night))?\b",
        r"\b(?:this|next)\s+(?:week(?:end)?|month)\b",
        r"\b(?:next\s+|this\s+)?(?:" + "|".join(WEEKDAYS) + r")\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b(?:" + "|".join(MONTHS) + r")\s+\d{1,2}(?:st|nd|rd|th)?\b",
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:" + "|".join(MONTHS) + r")\b",
        r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
    ]
    best: Optional[Tuple[int, str]] = None
    for p in pats:
        for m in re.finditer(p, t, re.I):
            if best is None or m.start() > best[0]:
                best = (m.start(), m.group(0))
    if best is None:
        return None
    value = best[1]
    return re.sub(r"^this\s+(?=(" + "|".join(WEEKDAYS) + r"))", "", value, flags=re.I)


def extract_time(text: str) -> Optional[str]:
    times = extract_times(text)
    return times[-1] if times else None


def extract_times(text: str) -> List[str]:
    """Clock times normalised to HH:MM (24h)."""
    out = []
    t = text or ""
    for m in re.finditer(r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?\s?m\.?|p\.?\s?m\.?)(?![a-z])", t, re.I):
        h, mi = int(m.group(1)), int(m.group(2) or 0)
        pm = m.group(3).lower().startswith("p")
        if h == 12:
            h = 0 if not pm else 12
        elif pm:
            h += 12
        if 0 <= h < 24 and 0 <= mi < 60:
            out.append(f"{h:02d}:{mi:02d}")
    for m in re.finditer(r"\b([01]?\d|2[0-3]):([0-5]\d)\b(?!\s*[ap]\.?m)", t, re.I):
        out.append(f"{int(m.group(1)):02d}:{m.group(2)}")
    if re.search(r"\bnoon\b", t, re.I):
        out.append("12:00")
    if re.search(r"\bmidnight\b", t, re.I):
        out.append("00:00")
    return out


def extract_person(text: str) -> Optional[str]:
    t = text or ""
    pats = [
        r"\b(?:passenger(?:'s)?(?:\s+name)?|name)\s+(?:is\s+|will\s+be\s+|:\s*)?(" + _CAP_SEQ + r")",
        r"\b(?:named|called|under(?:\s+the\s+name)?)\s+(" + _CAP_SEQ + r")",
        r"\bfor\s+(" + _CAP_SEQ + r")",
        r"\bit(?:'s| is)\s+for\s+(" + _CAP_SEQ + r")",
    ]
    found: List[Tuple[int, str]] = []
    for p in pats:
        for m in re.finditer(p, t):
            name = _clean_name(m.group(1))
            if name and not extract_date(name) and not extract_time(name):
                found.append((m.start(), name))
    if not found:
        return None
    found.sort()
    return found[-1][1]


def extract_codes(text: str) -> List[str]:
    """Identifier-looking tokens such as BK-0001, TK-12 or FL-DEN-8AM."""
    return re.findall(r"\b[A-Z]{1,5}(?:-[A-Z0-9]+)+\b", text or "")


def extract_numbers(text: str) -> List[Tuple[int, float]]:
    """[(position, value)] for digits and small number words."""
    out: List[Tuple[int, float]] = []
    t = text or ""
    for m in re.finditer(r"(?<![\w:\-])(\d+(?:\.\d+)?)(?![\w:])", t):
        out.append((m.start(), float(m.group(1))))
    low = t.lower()
    for word, val in sorted(NUMBER_WORDS.items(), key=lambda kv: -len(kv[0])):
        for m in re.finditer(r"\b" + re.escape(word) + r"\b", low):
            if not any(abs(p - m.start()) < 2 for p, _ in out):
                out.append((m.start(), float(val)))
    out.sort()
    return out


def number_for(text: str, arg_name: str, arg_desc: str = "") -> Optional[float]:
    """A number the user attached to this arg's noun, e.g. 'two nights' for `nights`."""
    nums = extract_numbers(text)
    if not nums:
        return None
    keys = {stem(w) for w in words(arg_name.replace("_", " ") + " " + arg_desc)} - STOPWORDS
    low = (text or "").lower()
    for pos, val in nums:
        tail = low[pos:pos + 40]
        following = [stem(w) for w in words(tail)[1:3]]
        if any(f in keys for f in following):
            return val
    return None


def find_enum(text: str, options: Sequence[Any]) -> Optional[Any]:
    low = (text or "").lower()
    hits = []
    for opt in options:
        o = str(opt).lower()
        m = re.search(r"(?<![a-z0-9])" + re.escape(o) + r"(?![a-z0-9])", low)
        if m:
            hits.append((m.start(), opt))
    if not hits:
        return None
    hits.sort()
    return hits[-1][1]


# ---------------------------------------------------------------------------
# selectors: "the 8 AM one", "the cheapest", "the second"
# ---------------------------------------------------------------------------
ORDINALS = {"first": 0, "second": 1, "third": 2, "fourth": 3, "last": -1, "1st": 0,
            "2nd": 1, "3rd": 2}


def selector_from_text(text: str) -> Dict[str, Any]:
    low = (text or "").lower()
    sel: Dict[str, Any] = {"times": extract_times(text), "codes": extract_codes(text)}
    for w, i in ORDINALS.items():
        if re.search(r"\b(?:the\s+)?" + re.escape(w) + r"\s+(?:one|option|flight|result)\b", low):
            sel["index"] = i
    if re.search(r"\b(?:cheapest|cheaper|lowest\s+price|least\s+expensive|budget)\b", low):
        sel["min_price"] = True
    if re.search(r"\b(?:earliest|earlier|morning)\b", low):
        sel["min_time"] = True
    if re.search(r"\b(?:latest|later|evening|afternoon)\b", low):
        sel["max_time"] = True
    return sel


def selector_is_empty(sel: Dict[str, Any]) -> bool:
    return not (sel.get("times") or sel.get("codes") or "index" in sel
                or sel.get("min_price") or sel.get("min_time") or sel.get("max_time"))


def _item_times(item: Dict[str, Any]) -> List[str]:
    out = []
    for v in item.values():
        if isinstance(v, str) and re.fullmatch(r"\d{1,2}:\d{2}", v.strip()):
            h, m = v.strip().split(":")
            out.append(f"{int(h):02d}:{m}")
    return out


def _item_price(item: Dict[str, Any]) -> Optional[float]:
    for k, v in item.items():
        if isinstance(v, (int, float)) and any(s in k.lower() for s in ("price", "usd", "cost", "fare", "rate")):
            return float(v)
    return None


def select_item(items: List[Dict[str, Any]], sel: Dict[str, Any]) -> Tuple[Optional[int], str]:
    """Pick one result item. Returns (index, reason); index None means ambiguous."""
    if not items:
        return None, "empty"
    if len(items) == 1:
        return 0, "only"
    codes = [c.lower() for c in sel.get("codes", [])]
    if codes:
        for i, it in enumerate(items):
            if any(isinstance(v, str) and v.lower() in codes for v in it.values()):
                return i, "code"
    times = sel.get("times") or []
    if times:
        for i, it in enumerate(items):
            if any(t in _item_times(it) for t in times):
                return i, "time"
        compact = []
        for t in times:
            h, m = int(t[:2]), t[3:]
            ampm = "AM" if h < 12 else "PM"
            h12 = h % 12 or 12
            compact.append(f"{h12}{ampm}" if m == "00" else f"{h12}{m}{ampm}")
        for i, it in enumerate(items):
            if any(isinstance(v, str) and any(c.lower() in v.lower() for c in compact)
                   for v in it.values()):
                return i, "time"
    if "index" in sel:
        idx = sel["index"]
        if -len(items) <= idx < len(items):
            return idx % len(items), "ordinal"
    if sel.get("min_price"):
        priced = [(p, i) for i, it in enumerate(items) if (p := _item_price(it)) is not None]
        if priced:
            return min(priced)[1], "price"
    if sel.get("min_time") or sel.get("max_time"):
        timed = [(t[0], i) for i, it in enumerate(items) if (t := _item_times(it))]
        if timed:
            return (min(timed) if sel.get("min_time") else max(timed))[1], "clock"
    return None, "ambiguous"


# ---------------------------------------------------------------------------
# small-talk and interruption cues
# ---------------------------------------------------------------------------
RETRACTION_CUES = (
    "never mind", "nevermind", "forget it", "forget that", "forget about it", "forget the",
    "forget about the", "cancel that", "cancel it", "cancel this", "don't bother",
    "dont bother", "scratch that", "no need", "skip it", "stop that", "stop it",
    "don't do that", "dont do that", "hold off", "not anymore", "i changed my mind",
    "call it off", "drop it", "leave it",
)
CORRECTION_CUES = ("actually", "instead", "make it", "change it", "change to", "switch to",
                   "i meant", "i mean", "sorry", "rather", "correction", "not ", "no,", "wait")
SMALLTALK = re.compile(
    r"^\s*(?:hi|hello|hey|thanks|thank you|good (?:morning|afternoon|evening)|ok(?:ay)?|cool|great|bye)\b"
    r"|what can you (?:do|help)|how can you help|who are you|what are you|help me\??\s*$",
    re.I)


def is_smalltalk(text: str) -> bool:
    return bool(SMALLTALK.search(text or ""))


def retraction_cue(text: str) -> Optional[Tuple[int, int]]:
    low = (text or "").lower()
    best = None
    for cue in RETRACTION_CUES:
        m = re.search(r"(?<![a-z])" + re.escape(cue) + r"(?![a-z])", low)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), m.end())
    return best


def remainder_after_retraction(text: str) -> str:
    """Text after the retraction clause: 'forget the flight, my TV is broken' -> 'my TV is broken'."""
    span = retraction_cue(text)
    if span is None:
        return text
    rest = (text or "")[span[1]:]
    m = re.search(r"[,.;:!?—–-]\s*|\b(?:and|but|because)\b\s*", rest)
    if m:
        return rest[m.end():].strip()
    # "forget the flight" with nothing after it
    return ""
