# Project conventions

<!-- The agent reads this at the start of every session. Keep it short and current.
     Graded: does it reflect how the team actually works? -->

## What this repository is
A receipt extraction and validation tool that sends receipt photos to an OpenRouter vision model, extracts structured JSON, and verifies the arithmetic and date constraints in pure code. See [`spec.md`](./spec.md).

## Commands
```bash
# test (unit tests, no API key needed)
pytest tests/test_checker.py -v

# eval (vision model evaluation, requires OPENROUTER_API_KEY)
pytest tests/test_eval.py -v

# run on a single receipt
python3 extract.py images/receipt-01.png

# lint
ruff check .
```

## Conventions
- Language: Python 3.10+
- Unit tests live in `tests/test_checker.py` and run without an API key in <0.2s.
- Model eval tests live in `tests/test_eval.py` and require `OPENROUTER_API_KEY`.
- Pure checker logic is kept separate from LLM/vision API calls.

## Working rules

- This is the Week 5 introductory lab. Stages assigned: intent, spec, plan,
  and tests. No branches or pull requests yet. Commit to main.
- Libraries and build tools are allowed. Name each dependency in spec.md
  under Dependencies, with the reason, before installing it; a hook blocks
  installs that spec.md does not list.
- images/ and images/expected.json are the answer key. Never edit them. If
  a test disagrees with the key, say so and stop.
- Tests live in tests/ (Python) or src/test (Java). Tests that call a model
  are marked and are skipped when no API key is set.

## Common mistakes
- Never edit or tamper with `images/` or `expected.json`.
- Do not make a vision API call per test; share the cached extraction across test assertions.
- Do not crash on non-JSON model output; catch and report errors gracefully.
- Do not let the model guess years when not printed on receipts.
