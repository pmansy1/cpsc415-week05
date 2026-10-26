# Intent: Receipts to data

## Goal
A program that takes a photograph of a receipt, queries a multimodal vision model to extract structured JSON (merchant, date, items with quantity and unit price, subtotal, discount, tax, and total), and validates in plain code that the item subtotals match the printed subtotal and that the subtotal, discount, and tax combine accurately into the total. Discrepancies are reported clearly rather than auto-repaired.

## Who it is for
Finance teams, auditors, and expense reporters who need reliable, automated extraction from receipt photos without trusting unchecked model outputs.

## Constraints
- Language: Python 3 (CLI tool and modular package).
- Multimodal Vision API: OpenRouter chat completion API with base64 image data URLs.
- Two comparison models: `minimax/minimax-m3` and `xiaomi/mimo-v2.6-flash`.
- Plain code validation: The checker must not use an LLM; all arithmetic and schema verification occurs in deterministic Python code.
- Discrepancy handling: The checker must report mathematical and formatting issues, not attempt to guess or fix them.
- Date handling: When a year is not printed on the receipt (e.g., informal or bake-sale receipts), the date must be reported as `null` rather than a guessed year.
- Non-JSON responses: A response that cannot be parsed as JSON must result in a clean, reported read failure, not an uncaught crash.
- Security: No API keys stored in source code; use `OPENROUTER_API_KEY` from environment variables.

## Not in scope
- Automatically fixing misread receipts or rewriting receipt totals.
- Optical Character Recognition (OCR) preprocessing libraries (e.g. Tesseract); extraction relies entirely on the multimodal vision LLM.
- Multi-receipt batch UI or web dashboard.
- Database persistence or bookkeeping accounting software integrations.

## Success looks like
1. Running `python3 extract.py <image_path>` outputs structured JSON, prints validation status (`CHECK: ok` or detailed discrepancies), and records token usage.
2. Fast test suite (`pytest tests/test_checker.py`) runs in <0.2 seconds without requiring an API key.
3. Eval test suite (`pytest tests/test_eval.py`) verifies all benchmark receipts against `images/expected.json` when `OPENROUTER_API_KEY` is provided, caching results so each image is evaluated with only one vision API call.
4. Arithmetic mismatches or missing fields trigger explicit diagnostics identifying the exact discrepancy.

## Open questions
None.

**Approved by:** Patrick Manswell, October 26, 2026
