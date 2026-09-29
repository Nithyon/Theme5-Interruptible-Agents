"""Manifest-driven argument handling.

Validates arguments against a tool's schema (the same checks as the mock, plus
basic types) and classifies what kind of value each argument needs, using only
the argument's name, type and description.
"""

from __future__ import annotations
from typing import Any, Dict, Iterator, List, Optional, Tuple

_LOCATION_WORDS = ("city", "destination", "location", "origin", "place", "airport", "pickup",
                   "dropoff", "town", "region", "country", "venue", "where")
_DATE_WORDS = ("date", "day", "when", "checkin", "check_in", "departure_date")
_TIME_WORDS = ("time", "hour", "slot")
_PERSON_WORDS = ("passenger", "guest", "customer", "traveler", "traveller", "person",
                 "full name", "contact name", "attendee")
_TEXT_WORDS = ("query", "summary", "description", "issue", "message", "question", "text",
               "note", "details", "reason", "problem", "symptom", "request", "comment")
_EMBED_WORDS = ("embedding", "vector", "image", "visual", "frame", "picture")


def arg_items(spec: Dict[str, Any]) -> Iterator[Tuple[str, Dict[str, Any]]]:
    for name, aspec in (spec.get("args") or {}).items():
        if isinstance(aspec, dict):
            yield name, aspec


def slot_name(path: str) -> str:
    """'device.model' -> 'device_model', 'destination' -> 'destination'."""
    return path.replace(".", "_")


def arg_kind(name: str, aspec: Dict[str, Any]) -> str:
    typ = str(aspec.get("type", "string")).lower()
    text = (name.replace("_", " ") + " " + str(aspec.get("description", ""))).lower()
    lname = name.lower()
    if typ == "object":
        return "object"
    if typ == "array":
        items = str(aspec.get("items", "")).lower()
        if items in ("number", "float", "integer") and any(w in text for w in _EMBED_WORDS):
            return "embedding"
        return "array"
    if typ == "boolean":
        return "boolean"
    if typ in ("number", "integer"):
        return "number"
    if aspec.get("enum"):
        return "enum"
    toks = set(lname.split("_"))
    if lname == "id" or lname.endswith("_id"):
        return "id"
    if toks & {"passenger", "guest", "customer", "traveler", "traveller", "person", "attendee"}:
        return "person"
    if "name" in toks and any(w in text for w in _PERSON_WORDS + ("name of the",)):
        if not any(w in text for w in ("device", "product", "model", "file", "hotel", "city")):
            return "person"
    if toks & set(_LOCATION_WORDS):
        return "location"
    if toks & set(_DATE_WORDS) or lname.endswith("date"):
        return "date"
    if toks & set(_TIME_WORDS):
        return "time"
    if toks & set(_TEXT_WORDS):
        return "text"
    if "model" in toks:
        return "model"
    if any(f" {w} " in f" {text} " for w in ("city", "airport", "location")):
        return "location"
    return "string"


def location_role(name: str, aspec: Dict[str, Any]) -> str:
    text = (name + " " + str(aspec.get("description", ""))).lower()
    if any(w in text for w in ("origin", "from", "departure city", "departing")):
        return "origin"
    if any(w in text for w in ("pickup", "pick-up", "pick up")):
        return "pickup"
    if any(w in text for w in ("destination", "arrival", "to ")):
        return "destination"
    return "any"


def _type_ok(val: Any, typ: str) -> bool:
    if typ == "string":
        return isinstance(val, str)
    if typ in ("number", "float"):
        return isinstance(val, (int, float)) and not isinstance(val, bool)
    if typ == "integer":
        return isinstance(val, int) and not isinstance(val, bool)
    if typ == "boolean":
        return isinstance(val, bool)
    if typ == "array":
        return isinstance(val, list)
    if typ == "object":
        return isinstance(val, dict)
    return True


def validate(spec: Dict[str, Any], args: Dict[str, Any]) -> List[str]:
    """Problems with `args` for this tool ([] = valid)."""
    problems: List[str] = []
    if not isinstance(args, dict):
        return ["args must be an object"]
    for name, aspec in arg_items(spec):
        problems.extend(_validate_one(name, aspec, args))
    return problems


def _validate_one(path: str, aspec: Dict[str, Any], container: Dict[str, Any]) -> List[str]:
    name = path.split(".")[-1]
    if name not in container or container[name] is None:
        return [f"missing required '{path}'"] if aspec.get("required") else []
    val = container[name]
    typ = str(aspec.get("type", "string")).lower()
    problems = []
    if not _type_ok(val, typ):
        problems.append(f"'{path}' must be {typ}")
        return problems
    if typ == "string" and not val.strip():
        problems.append(f"'{path}' is empty")
    if "enum" in aspec and val not in aspec["enum"]:
        problems.append(f"'{path}' must be one of {aspec['enum']}")
    if typ == "array":
        item_t = str(aspec.get("items", "")).lower()
        if item_t and any(not _type_ok(v, item_t) for v in val):
            problems.append(f"'{path}' items must be {item_t}")
    if typ == "object":
        for sub, sspec in (aspec.get("properties") or {}).items():
            if isinstance(sspec, dict):
                problems.extend(_validate_one(f"{path}.{sub}", sspec, val))
    return problems


def missing_required(spec: Dict[str, Any], args: Dict[str, Any]) -> List[str]:
    """Dotted paths of required args (and nested fields) that are absent."""
    out: List[str] = []

    def walk(prefix: str, props: Dict[str, Any], container: Any):
        for name, aspec in props.items():
            if not isinstance(aspec, dict):
                continue
            path = f"{prefix}{name}"
            present = isinstance(container, dict) and container.get(name) not in (None, "", [], {})
            is_obj = str(aspec.get("type")) == "object" and aspec.get("properties")
            if is_obj and (present or aspec.get("required")):
                walk(path + ".", aspec.get("properties") or {},
                     container.get(name) if present else {})
            elif aspec.get("required") and not present:
                out.append(path)

    walk("", spec.get("args") or {}, args)
    return out


def human(path: str) -> str:
    """'passenger_name' -> 'passenger name', 'issue.severity' -> 'issue severity'."""
    return path.replace(".", " ").replace("_", " ").strip()


def humanize_tool(name: str) -> str:
    return name.replace("_", " ").strip()


def find_arg_spec(spec: Dict[str, Any], path: str) -> Optional[Dict[str, Any]]:
    parts = path.split(".")
    cur = spec.get("args") or {}
    aspec = None
    for i, p in enumerate(parts):
        aspec = cur.get(p) if isinstance(cur, dict) else None
        if not isinstance(aspec, dict):
            return None
        cur = aspec.get("properties") or {}
    return aspec
