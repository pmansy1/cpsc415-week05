# Plan

## Files to create or change
| File | Purpose |
|---|---|
| `receipts/__init__.py` | Package initialization exporting reader and checker functions |
| `receipts/checker.py` | Pure deterministic Python validation of items, subtotals, totals, and date formatting |
| `receipts/reader.py` | Multimodal API client for OpenRouter, image base64 encoder, robust JSON parser |
| `extract.py` | CLI entry point: reads receipt image, runs extraction and validation, prints formatted JSON and diagnostics |
| `tests/conftest.py` | Shared pytest fixtures and test configuration |
| `tests/test_checker.py` | Unit tests for checker logic and JSON parsing (NO key needed) |
| `tests/test_eval.py` | Multimodal model evaluation against `images/expected.json` (NEEDS key) |
| `CHECKS.md` | Verification record of test outputs, model comparison, linter run, and step-4 tamper test |
| `README.md` | Usage guide, test instructions, two-model comparison, and explanation of checks/hooks |

## Order of work
1. **Offline Unit Tests First (Red):** Write `tests/test_checker.py` testing item arithmetic, total calculation, discount sign handling, date formatting/null validation, non-JSON handling, and prose extraction. Run `pytest tests/test_checker.py` and confirm failure.
2. **Offline Implementation (Green):** Implement `receipts/checker.py` and the parsing helper in `receipts/reader.py`. Run `pytest tests/test_checker.py` and confirm all pass in <0.2s.
3. **Model Integration & Eval Tests First (Red):** Write `tests/test_eval.py` asserting merchant, date, item count, total, and zero checker errors against `images/expected.json`. Write `extract.py`. Run tests.
4. **Model Integration Implementation (Green):** Implement full `receipts/reader.py` (with reasoning parameter control for `xiaomi/mimo-v2.6-flash` vs `minimax/minimax-m3`). Run eval suite on `minimax/minimax-m3` and record in `CHECKS.md`.
5. **Model Comparison:** Run eval on `xiaomi/mimo-v2.6-flash`. Record token counts, latency, and accuracy differences in `CHECKS.md`.
6. **Step 4 Intentional Break:** Temporarily tamper with `receipt-01.png` total in `images/expected.json` (13.96 vs 13.66). Test and document agent refusal via guardrail hook. Restore key.
7. **Step 5 Own Receipts:** Add two real receipts in `my-receipts/` with hand-written `my-receipts/expected.json`. Run eval and record findings.
8. **Lint and Documentation:** Run `ruff check .`, finalize `CHECKS.md` and `README.md`.

## Risks
1. **Xiaomi MiMo Hidden Reasoning Loop:** `xiaomi/mimo-v2.6-flash` can spend its entire token budget thinking and output empty text. *Mitigation:* Ensure `body["reasoning"] = {"enabled": False}` is set for this model.
2. **MiniMax Faded Date Misread:** Disabling reasoning globally causes `minimax/minimax-m3` to miss faded dates. *Mitigation:* Keep reasoning enabled on MiniMax M3.
3. **Discount Sign Inconsistency:** Receipts print discounts either as positive subtractions or negative amounts. *Mitigation:* The checker normalizes discount signs (`abs(discount)` deducted from subtotal).
4. **Answer Key Disagreement:** If a model reads an image correctly but `expected.json` has a discrepancy, modifying `expected.json` is blocked by the guard hook. *Mitigation:* Document the discrepancy in `CHECKS.md` rather than weakening code or modifying the key.

## Proof

### Tests running WITHOUT an API key (`tests/test_checker.py`)
- **What they test:**
  - Item math: multiple items with quantity and price sum to subtotal.
  - Subtotal/tax/discount math: `subtotal - discount + tax == total` within $0.02.
  - Negative discount sign normalization.
  - Rejection of invalid arithmetic with explicit discrepancy messages.
  - Null date when year is missing; validation of `YYYY-MM-DD` when present.
  - Robust JSON parsing: extracting clean JSON from markdown fences (```` ```json ... ``` ````) and conversational prose.
  - Graceful failure when model output is non-JSON or malformed (returns error, does not crash).
- **What they prove on their own:**
  - The deterministic validation engine and parsing logic are 100% correct and reliable under all edge cases without spending money or relying on external network availability.

### Tests needing an API key (`tests/test_eval.py`)
- **What they test:**
  - Real end-to-end extraction against all benchmark images in `images/` (and `my-receipts/`).
  - Caches one vision API call per image across all five checks (merchant, date, items count, total, checker status).
  - Skips cleanly via `pytest.mark.skipif` when `OPENROUTER_API_KEY` is not present in the environment.
- **What they prove:**
  - The multimodal vision model accurately perceives real-world receipt photographs (including tilted, crumpled, and faded text) and complies with the required structured JSON schema.

## Key Questions Addressed
1. *Which tests run without the key, and what do they prove on their own?*
   - `tests/test_checker.py` runs completely offline without any API key. It proves that the arithmetic validation logic, schema enforcement, date validation, and JSON text parsing work accurately across normal and pathological edge cases.
2. *What does the eval compare against, and what if the model is right and `expected.json` is wrong?*
   - The eval compares extracted merchant name, date string/null, item count, total price, and absence of checker errors against `images/expected.json`. If the model read the receipt accurately but `expected.json` has an error, the agent must NEVER edit `expected.json` (enforced by `guard.py`); instead, it must report the conflict clearly in `CHECKS.md` and stop.
3. *What could break in step N, and how would I notice?*
   - In Step 4 (model comparison), if `xiaomi/mimo-v2.6-flash` fails to output JSON because it ran out of tokens while thinking, the reader will capture the empty response and output an informative error. We notice immediately because `pytest` fails with a non-JSON read failure.
4. *Why this library, and what would we write by hand without it?*
   - We use `pytest` as the test runner to provide clean test discovery, fixture caching (one vision call per receipt), parametrized test cases, and skip logic (`@pytest.mark.skipif`). Without `pytest`, we would have to write a custom test runner harness with manual exception handling, reporting, and CLI flags.

## Subagents and parallel work
None required. All tasks execute sequentially in accordance with TDD principles.

**Approved by:** Patrick Manswell, October 26, 2026
