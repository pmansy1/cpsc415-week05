# Spec

## Intent
Implements [`intent/receipts.md`](./intent/receipts.md).

## Components

### 1. Receipt Reader (`receipts.reader`)
- **What it does:** Encodes receipt images as base64 data URLs, formats multimodal chat completion requests, calls the OpenRouter API, and parses the returned JSON payload.
- **Language:** Python 3. **Why:** Python includes built-in standard library modules (`base64`, `json`, `urllib.request`, `pathlib`) that execute HTTP calls and JSON manipulation without third-party bloat, while integrating seamlessly with pytest.
- **Model Decision:**
  - Primary Model: `minimax/minimax-m3`. **Why:** High multimodal OCR fidelity on faded and tilted print, reads dates reliably with default/extended reasoning enabled, and costs only ~$0.0003 per receipt.
  - Comparison Model: `xiaomi/mimo-v2.6-flash`. **Why:** Extremely fast and inexpensive (~$0.0001 per receipt), but requires `body["reasoning"] = {"enabled": False}` to prevent exhaustively consuming the output token budget in hidden reasoning loops.
- **Interfaces:**
  - `encode_image(image_path: Path) -> str`: Returns base64 data URL with proper MIME type.
  - `extract_receipt(image_path: Path, model: str | None = None) -> tuple[dict | None, dict, str | None]`: Returns `(receipt_data, usage_metadata, error_message)`.
  - `parse_model_response(raw_text: str) -> dict`: Extracts JSON dictionary even if wrapped in markdown code blocks or conversational prose; raises `ValueError` on invalid JSON.
- **Dependencies:** Standard library (`json`, `urllib.request`, `base64`, `os`, `pathlib`, `re`).

### 2. Receipt Checker (`receipts.checker`)
- **What it does:** Pure Python deterministic verification of receipt schema and arithmetic consistency. Does not invoke any LLM.
- **Language:** Python 3. **Why:** Deterministic, reproducible, millisecond execution, testable completely offline without API keys or costs.
- **Model:** None (pure deterministic code).
- **Interfaces:**
  - `validate_receipt(data: dict) -> tuple[bool, list[str]]`: Returns `(is_valid, list_of_discrepancies)`.
- **Dependencies:** Standard library (`math`, `re`).

## Dependencies
- `pytest`: Python test runner used to execute fast offline unit tests (`tests/test_checker.py`) and model eval tests (`tests/test_eval.py`).
- `ruff`: Fast Python linter used to enforce code cleanliness, formatting, and identify syntax or style flaws.

## Behavior

1. **Non-JSON Graceful Handling:** If the vision model returns non-JSON text, an error or markdown without JSON, the reader surfaces a failed read error rather than crashing the program.
2. **Prose and Fences Extraction:** If the model returns valid JSON enclosed within markdown triple backticks (```` ```json ... ``` ````) or surrounding explanatory prose, the JSON parser extracts and parses the JSON block correctly.
3. **Null Date for Missing Year:** If a receipt has a date without a year printed (such as "Oct 3"), `date` must be parsed or reported as `null` (not a guessed or fabricated year).
4. **Item Arithmetic Validation:** For all items with `qty` (or `quantity`) and `price` (or `unit_price`), `sum(qty * price)` must match `subtotal` within $0.02 tolerance.
5. **Total Arithmetic Validation:** The relation `subtotal - discount + tax == total` must hold within $0.02 tolerance (where discount is treated as positive deduction; negative values are normalized). If the numbers do not add up, the checker reports the exact calculated versus stated values.
6. **Discrepancy Reporting:** The checker reports problems with clear diagnostic messages and does not alter or attempt to auto-repair the data.
7. **Graceful Skipped Tests:** When `OPENROUTER_API_KEY` is not set, eval tests that call the model are marked and skipped cleanly with pytest, leaving no failures.
8. **Single Model Call Per Image:** Model evaluation tests cache and reuse the model extraction per image to prevent redundant token charges.

## Failure handling
- **API Errors & Timeouts:** OpenRouter HTTP 4xx/5xx errors or network timeouts are trapped and reported as reader failures.
- **Empty or Truncated Responses:** Handled as failed reads with descriptive messages.
- **Malformed Data:** If numbers are non-numeric strings or required fields are omitted, the checker records an explicit schema violation.

## Cost estimate
- Receipt image input: ~750 tokens in (~$0.0002).
- Structured output: ~250 tokens out (~$0.0001).
- 5 benchmark receipts evaluated: ~$0.0015 total.
- Typical semester testing usage (500 runs): under $1.00.

## Out of scope
- Automatic image preprocessing (deskewing, binarization).
- Attempting to auto-correct erroneous receipts.
- Multi-currency conversion or live exchange rates.

**Approved by:** Patrick Manswell, October 26, 2026

---

## Week 6: image set

Implements [`intent/image-set.md`](./intent/image-set.md). Code lives in `week06/`.

### 3. Generator (`week06/generate.py`)
- **What it does:** Reads `prompts.json` (five prompts, each with a seed, yes/no requirements and the expected placard text). Calls OpenRouter's **Image API** once per prompt, saves each image, and writes `images/manifest.json` with prompt, seed, model, media type, file, seconds and the cost from the reply's `usage.cost`.
- **Language:** Python 3. **Why:** the same language as my Week 5 reader and FitLab's backend, so the checker can move into the team repository unchanged. Alternative: Java with `java.net.http`. Permitted, but I would write the Image API request by hand, and FitLab is Python.
- **Model:**
  - Default: `black-forest-labs/flux.2-klein-4b`. **Why:** cheap (about $0.014 per image on Oct 19, 2026), accepts a seed, and is fast enough to generate five images in one sitting.
  - Comparison: `google/gemini-3.1-flash-lite-image`, run on **one** prompt with the same seed. **Why:** FitLab's generator uses the Gemini image family, so this shows how the class default compares with ours on the same requirements. It is priced per image token, about $0.03–0.04 per image.
- **Interfaces:** `python3 generate.py prompts.json --out images [--model M]`. With no `OPENROUTER_API_KEY` it prints one line and exits 1; nothing is billed.
- **Dependencies:** `openrouter` (see Dependencies).

### 4. Critic-checker (`week06/checker.py`, `week06/critique.py`)
- **What it does:** For each image in the manifest, sends the image plus a yes/no **checklist** made from that prompt's requirements to a vision model and asks for JSON. Then asks a second, **narrow** question: "write the text on the placard exactly as printed". Plain code (`checker.py`, no model, no key) then:
  - extracts the JSON,
  - checks every requirement was answered, none was invented, and each was met,
  - compares the placard read with the expected text.

  With `--compare`, it lists every requirement and text read where two critique files disagree.
- **Language:** Python 3, for the same reasons as the generator. The checker is pure functions so it can be tested without a key.
- **Model:**
  - Critic: `minimax/minimax-m3`, with reasoning **on**. **Why:** it was the stronger reader in my Week 5 receipt lab.
  - Second model to check the critic: `xiaomi/mimo-v2.6-flash`, with reasoning **off** (`reasoning={"effort": "none"}` in the SDK, or the reply is empty). **Why:** a different vendor and much cheaper. Where they disagree, a person looks.
- **Interfaces:**
  - `python3 critique.py images/manifest.json [--model M] [--out FILE]`
  - `python3 critique.py --compare A.json B.json` (no key needed)
  - `checker.py` exposes `extract_json`, `check_checklist`, `text_matches` and `disagreements`.
- **Dependencies:** `openrouter`, imported only on the billed path, so the tests never need it.

### Week 6 dependencies
- `openrouter`: the OpenRouter Python SDK. **Why:** the Image API (`client.images.generate`) has its own request and reply shape (`data[0].b64_json`, `media_type`, `usage.cost`). The SDK types it, and the same client sends the chat request with an image part for the critique. Hand-written `urllib` would duplicate both request shapes and their error handling. Imported lazily, so no-key runs work without it installed.

### Week 6 behaviors
9. **A critique that is not JSON is a failed critique, not a crash.** The checker reports every requirement as unanswered.
10. **JSON inside prose or code fences is extracted** and checked normally.
11. **A requirement the critic did not answer is a problem**, even if every answered item is met.
12. **A requirement the critic invented** (an item not in the checklist) is a problem.
13. **An unmet requirement is reported by name.**
14. Requirement text is matched **after normalizing case and punctuation**, so "there is a mannequin." answers "There is a mannequin".
15. **Expected text is compared in code, not by the critic:** the model only reads the placard back. `"WEDDING"` vs `"WEDOING"` is a mismatch. Case and punctuation are ignored, letters are not.
16. **`--compare` reports every requirement and text read where two critique files disagree**, and nothing when they agree.
17. **No key means no billed call:** `generate.py` and `critique.py` exit 1 with one line. Tests that would call a model are skipped.
18. **The manifest records prompt, seed, model, media type and cost per image.** Cost comes from the reply's `usage.cost`, not an estimate.

### Week 6 failure handling
- An empty reply, or one cut off at the token limit (`finish_reason == "length"`), is recorded with its usage and counted as a failed critique.
- An Image API error stops the run with the HTTP status. The images already saved, and a manifest for them, are kept.

### Week 6 cost estimate
- Five FLUX images: about $0.07. One comparison image: about $0.04.
- Five m3 critiques plus five placard reads: about $0.005. The same on mimo: about $0.001.
- **One full eval: about $0.12.** If it is run in a loop by mistake, each pass costs another $0.12, so nothing calls a model from inside the tests.
