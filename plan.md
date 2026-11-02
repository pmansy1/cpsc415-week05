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

---

# Week 6

## Files to create or change
| File | Purpose |
|---|---|
| `week06/checker.py` | Pure functions: `extract_json`, `check_checklist`, `text_matches`, `disagreements`. No model, no key. |
| `week06/tests/conftest.py` | Makes `week06/` importable from the tests. |
| `week06/tests/test_checker.py` | No-key tests for every Week 6 behavior (9–16). |
| `week06/tests/test_cli.py` | No-key tests that both scripts exit 1 with no key, and that `--compare` runs without one (behavior 17). |
| `week06/generate.py` | Image API calls; writes `images/manifest.json`. |
| `week06/critique.py` | Vision calls (checklist plus the narrow placard read); `--compare`. |
| `week06/prompts.json` | Five occasion prompts, seeds 601–605, requirements, expected placard text. |
| `week06/images/`, `week06/images-nb/`, `week06/images-seed/` | Generated images and manifests (FLUX set, comparison model, seed re-run). |
| `week06/critique.json`, `week06/critique-mimo.json` | Critiques from both vision models. |
| `week06/CHECKS.md` | Per-image results, the seed check, the comparison model, the critic checked, ruff, the Review. |

## Order of work
1. Tests for `checker.py` (behaviors 9–16). Run them and watch them **fail**.
2. `checker.py` until green. Run `ruff check .`. Commit `Image set: checker with tests`.
3. Tests for the no-key exits (17), then `generate.py` and `critique.py`.
4. `prompts.json`. Look at it once more: are the requirements yes/no and visible?
5. Billed eval: five FLUX images, then five m3 critiques. Look at the images **before** reading the critiques.
6. Seed re-run of one prompt and the comparison model on one prompt.
7. The mimo critiques, `--compare`, an open-ended critique of one image, and CHECKS.md.
8. Team repo: branch `week06-patrick`, tests first, PR, reviewer, replies, teammate approval.

## Risks
- **The critic is wrong and the code can't tell.** The code knows only whether the critic answered the checklist, not whether its answers are true. A wrong "met" is caught only by the second model or by a person (see Q1).
- **Image models misspell short words on signs.** That is the point of the placard read, but a misspelled placard in an otherwise good image is a real failure, not a bug in the checker.
- **Reasoning settings.** mimo with reasoning on returns an empty reply, and m3 needs it on. A wrong setting looks like "not JSON" every time.
- **A billed loop.** Any model call inside a test, or a rerun loop in a script, multiplies the cost (see Q2).
- **The guard is permissive.** It looks for the package name anywhere in `spec.md`, so "OpenRouter" in prose already lets `openrouter` through. I'll note it in CHECKS.md rather than change a Week 5 artifact.

## Proof
### No key (free, under a second, run by the gate)
- `test_checker.py`: all met → ok; one unmet → named; one requirement missing → problem; one invented → problem; reply not JSON → failed critique with every requirement missing, no exception; JSON inside prose and fences → extracted; requirement text matched after normalizing; `"WEDDING"` vs `"WEDOING"` → mismatch; two critique files → the exact disagreements, and none for identical files. **Proves:** the code's comparison is right. **Cost:** $0.
- `test_cli.py`: both scripts exit 1 with no key; `--compare` works without one. **Proves:** nothing is billed by accident. **Cost:** $0.

### Billed eval (run by a person, results go in CHECKS.md)
- Five FLUX generations plus five m3 critiques (checklist and placard read): **about $0.075**.
- Seed re-run of one prompt: about $0.014. Comparison model on one prompt: about $0.04.
- Five mimo critiques: about $0.001.
- **Total about $0.13.** **Proves:** what the models actually do on our prompts. It doesn't prove the checker, because the no-key tests already do that.

## Questions asked of the plan, and the answers
1. **"If the critic says a requirement is unmet and it is actually met, which test notices?"** No automated test can. The no-key tests prove the code reports what the critic said, not whether the critic was right. It is noticed by the **second model disagreeing** (`--compare`) and then by **me looking at the image**. That disagreement-then-look step is now step 7 of the order of work, with a CHECKS.md line per disagreement.
2. **"What does one run of the eval cost, and what happens if I run it in a loop by mistake?"** About $0.09 for the five images plus both critique sets, and each extra pass repeats it. Corrections made: no test calls a model; the scripts exit with no key; the gate strips the key; and my OpenRouter key has a credit limit.
3. **"What does the same seed guarantee, and how would I check that?"** The same model, prompt and seed should give the same *picture*. It is not promised to give the same *bytes*, because JPEG encoding can differ. Check both: look at the two images side by side, and `cmp` the files. Record both answers.

**Approved by:** Patrick Manswell, November 2, 2026
