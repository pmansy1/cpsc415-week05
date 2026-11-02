"""Critique a generated image set with a vision model, then check the critique in code.

    python3 critique.py images/manifest.json                            # minimax/minimax-m3, needs a key
    python3 critique.py images/manifest.json --model xiaomi/mimo-v2.6-flash --out critique-mimo.json
    python3 critique.py --compare critique.json critique-mimo.json      # no key: where the critics disagree

Each image gets two questions: a yes/no checklist made from its requirements (JSON only),
and a narrow read of the placard text. checker.py then compares the answers with what was
asked for. A reply that is not JSON is a failed critique, not a crash.
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path

from checker import check_checklist, disagreements, extract_json, text_matches

DEFAULT_MODEL = "minimax/minimax-m3"
# Hidden reasoning is per model: mimo must have it off or the reply is empty; m3 needs it on.
# The SDK's reasoning object only knows "effort", so "none" is how it is turned off.
REASONING = {"xiaomi/mimo-v2.6-flash": {"effort": "none"}}

CHECKLIST_PROMPT = """You are checking a generated image against the prompt that produced it.
Prompt: {prompt}

Answer every item below with true or false, strictly from what is visible in the image.
Reply with one JSON object and nothing else:
{{"checks": [{{"requirement": "<item text, copied exactly>", "met": true, "evidence": "<one short sentence>"}}]}}

Items:
{items}"""

TEXT_PROMPT = ("Read the text printed on the placard or sign in this image exactly as printed, "
               "character for character. Reply with that text only. If there is no placard, reply NONE.")


def ask(client, model: str, image: Path, media_type: str, question: str, max_tokens: int) -> tuple[str | None, dict]:
    """One vision call through the chat endpoint: the question plus the image as a data URL."""
    data = base64.b64encode(image.read_bytes()).decode()
    extra = {"reasoning": REASONING[model]} if model in REASONING else {}
    reply = client.chat.send(model=model, max_tokens=max_tokens, messages=[{"role": "user", "content": [
        {"type": "text", "text": question},
        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{data}"}}]}], **extra)
    usage = {}
    if reply.usage:
        usage = {"in": reply.usage.prompt_tokens, "out": reply.usage.completion_tokens,
                 "cost": getattr(reply.usage, "cost", None)}
    usage["finish"] = reply.choices[0].finish_reason     # "length" means the budget ran out mid-answer
    return reply.choices[0].message.content, usage


def critique_one(client, model: str, folder: Path, entry: dict) -> dict:
    image = folder / entry["file"]
    items = "\n".join(f"- {r}" for r in entry["requirements"])
    raw, usage = ask(client, model, image, entry["media_type"],
                     CHECKLIST_PROMPT.format(prompt=entry["prompt"], items=items), max_tokens=2000)
    critique = extract_json(raw)
    result = {"name": entry["name"], "model": model, "critique": critique, "raw": raw,
              "usage": usage, "check": check_checklist(entry["requirements"], critique)}
    if entry.get("expected_text"):
        read, text_usage = ask(client, model, image, entry["media_type"], TEXT_PROMPT, max_tokens=600)
        result["text_read"] = (read or "").strip()
        result["text_matches"] = text_matches(entry["expected_text"], read)
        result["usage_text"] = text_usage
    return result


def summary(result: dict) -> str:
    verdict = "ok" if result["check"]["ok"] else "; ".join(result["check"]["problems"])
    if result["check"]["unmet"]:
        verdict += f" (unmet: {result['check']['unmet']})"
    if "text_read" in result:
        verdict += f"  placard read {result['text_read']!r} ({'match' if result['text_matches'] else 'MISMATCH'})"
    return f"{result['name']}: {verdict}"


def compare(path_a: Path, path_b: Path) -> None:
    diffs = disagreements(json.loads(path_a.read_text()), json.loads(path_b.read_text()))
    for d in diffs:
        print(d["name"])
        for x in d["diffs"]:
            print(f"  {x['requirement']}: {x['a']!r} vs {x['b']!r}")
    print(f"{len(diffs)} image(s) where the two critics disagree. Look at those yourself.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("manifest", nargs="?", type=Path)
    ap.add_argument("--model", default=os.environ.get("CRITIC_MODEL", DEFAULT_MODEL))
    ap.add_argument("--out", type=Path, default=Path("critique.json"))
    ap.add_argument("--compare", nargs=2, type=Path, metavar=("A.json", "B.json"))
    args = ap.parse_args()

    if args.compare:
        compare(*args.compare)
        return
    if args.manifest is None:
        ap.error("manifest.json is required (or use --compare)")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set; each critique is a billed vision call. Nothing checked.")
    from openrouter import OpenRouter          # imported here so the no-key path never needs it

    client = OpenRouter(api_key=key)
    results = []
    for entry in json.loads(args.manifest.read_text()):
        result = critique_one(client, args.model, args.manifest.parent, entry)
        results.append(result)
        print(summary(result))
    args.out.write_text(json.dumps(results, indent=2) + "\n")
    bad = [r["name"] for r in results if not r["check"]["ok"] or r.get("text_matches") is False]
    print(f"{len(results) - len(bad)}/{len(results)} image(s) pass the code's check; written to {args.out}")


if __name__ == "__main__":
    main()
