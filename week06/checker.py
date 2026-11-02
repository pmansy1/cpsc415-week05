"""Plain code that checks a vision model's critique. No model, no key, no network.

The critic is a model, so its answer is data to be checked, not a verdict. This module
can say whether the critic answered every requirement, answered only those, and said
each was met, and whether the text it read back matches the text the prompt asked for.
It cannot say whether the critic was right; a second model and a person do that.
"""
import json
import re

NOT_A_CHECKLIST = "critique was not the JSON checklist that was asked for"


def extract_json(text: str | None) -> dict | None:
    """The JSON object inside a reply (bare, fenced, or wrapped in prose), or None."""
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def normalize(text: str) -> str:
    """Lower case, punctuation and extra spaces removed; letters and digits kept."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _answers(critique: dict) -> dict[str, dict]:
    return {normalize(c["requirement"]): c for c in critique["checks"]
            if isinstance(c, dict) and isinstance(c.get("requirement"), str)}


def check_checklist(requirements: list[str], critique: object) -> dict:
    """Compare the critic's checklist with the requirements it was given."""
    if not isinstance(critique, dict) or not isinstance(critique.get("checks"), list):
        return {"ok": False, "problems": [NOT_A_CHECKLIST], "unmet": [],
                "missing": list(requirements), "extra": []}
    answered = _answers(critique)
    wanted = {normalize(r): r for r in requirements}
    missing = [r for key, r in wanted.items() if key not in answered]
    extra = [c["requirement"] for key, c in answered.items() if key not in wanted]
    unmet = [r for key, r in wanted.items() if key in answered and answered[key].get("met") is not True]
    problems = []
    if missing:
        problems.append(f"critic did not answer {len(missing)} requirement(s)")
    if extra:
        problems.append(f"critic answered {len(extra)} item(s) that were not asked")
    if unmet:
        problems.append(f"{len(unmet)} requirement(s) reported unmet")
    return {"ok": not problems, "problems": problems, "unmet": unmet, "missing": missing, "extra": extra}


def text_matches(expected: str, read: str | None) -> bool:
    """True when the text the model read back is the expected text, ignoring case and punctuation."""
    return bool(read) and normalize(expected) == normalize(read)


def _verdicts(entry: dict) -> dict:
    checks = (entry.get("critique") or {}).get("checks") or []
    return {normalize(c["requirement"]): c.get("met") for c in checks
            if isinstance(c, dict) and isinstance(c.get("requirement"), str)}


def _labels(entry: dict) -> dict:
    checks = (entry.get("critique") or {}).get("checks") or []
    return {normalize(c["requirement"]): c["requirement"] for c in checks
            if isinstance(c, dict) and isinstance(c.get("requirement"), str)}


def disagreements(a: list[dict], b: list[dict]) -> list[dict]:
    """Images where two critique files differ on any requirement or on the text read."""
    by_name = {entry["name"]: entry for entry in b}
    out = []
    for entry_a in a:
        entry_b = by_name.get(entry_a["name"])
        if entry_b is None:
            continue
        va, vb = _verdicts(entry_a), _verdicts(entry_b)
        labels = {**_labels(entry_b), **_labels(entry_a)}
        diffs = [{"requirement": labels[k], "a": va.get(k), "b": vb.get(k)}
                 for k in sorted(set(va) | set(vb)) if va.get(k) != vb.get(k)]
        if entry_a.get("text_read") != entry_b.get("text_read"):
            diffs.append({"requirement": "<text read>", "a": entry_a.get("text_read"),
                          "b": entry_b.get("text_read")})
        if diffs:
            out.append({"name": entry_a["name"], "diffs": diffs})
    return out
