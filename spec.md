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
