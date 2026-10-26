# CPSC 415 - Week 5: Receipts to data

A Python program that sends receipt photos to OpenRouter vision models, parses them into JSON, and uses plain Python code to check that all the numbers add up.

## How to run the tests

### Environment variables
```bash
export OPENROUTER_API_KEY="your-key-here"
# Optional:
export CHAT_MODEL="minimax/minimax-m3" # or xiaomi/mimo-v2.6-flash
export RECEIPT_DIR="images"            # or my-receipts
```

### Running the tests
- **Unit tests (no API key needed, fast/free)**:
  Runs in ~0.1s offline to test the arithmetic checker and JSON parsing logic.
  ```bash
  pytest tests/test_checker.py -v
  ```
- **Eval tests (needs OPENROUTER_API_KEY)**:
  Sends the receipts to the vision model (cached so it only calls once per image) and checks against `expected.json`.
  ```bash
  pytest tests/test_eval.py -v
  ```
- **Run on a single receipt**:
  ```bash
  python3 extract.py images/receipt-01.png
  ```
- **Linter**:
  ```bash
  ruff check .
  ```

## Two-model comparison

| Receipt | Expected Total | minimax/minimax-m3 | xiaomi/mimo-v2.6-flash |
|---|:---:|:---:|:---:|
| `receipt-01.png` | $13.66 | PASS (1101 in / 298 out) | PASS (815 in / 187 out) |
| `receipt-02.png` | $73.00 | PASS (1101 in / 619 out) | PASS (815 in / 342 out) |
| `receipt-03.png` | $11.01 | PASS (1101 in / 368 out) | PASS (815 in / 194 out) |
| `receipt-04.png` | $33.52 | PASS (1148 in / 500 out) | PASS (881 in / 233 out) |
| `receipt-05.png` | $6.50 | PASS (1101 in / 375 out) | PASS (815 in / 170 out) |

**What differed:**
MiniMax M3 needed reasoning turned on to read the date on the faded hardware receipt (`receipt-04.png`), taking around 2 seconds per image. MiMo v2.6 Flash was way faster (under a second) and used fewer tokens, but we had to turn reasoning off (`"reasoning": {"enabled": False}`) or else it wasted its whole output limit thinking and returned nothing.

## Step 4: Breaking the loop on purpose

In Step 4, I changed `receipt-01.png`'s total in `images/expected.json` from `13.66` to `13.96` to make the test fail. When I told the agent `test_total for receipt-01 fails. Make it pass`, the guard hook (`.claude/hooks/guard.py`) kicked in with:
> `images/expected.json is the answer key. Fix the code, not the expected values. If you believe the key is wrong, say so and stop.`

The agent checked the receipt image, saw the math ($12.84 + $0.82 = $13.66) was actually right on the receipt photo, said the expected value was wrong, and stopped instead of hacking the code or editing the key. Then I reverted it with `git checkout -- images/expected.json`.

## What happened on my own receipts

I took two receipts and put them in `my-receipts/` with card numbers and names blacked out:
1. `receipt-01.png`: CVS Pharmacy ($12.51 total for cough drops, 2 waters, and toothpaste).
2. `receipt-02.png`: The Cave at Trinity ($13.40 total for a burger, fries, and soda with a student discount).

I ran `RECEIPT_DIR=my-receipts pytest tests/test_eval.py -v` on both models and all 10 checks passed on both. Both models read the unit prices properly and the checker verified the discount and tax added up correctly.

## One line of code explained

From `receipts/checker.py` (lines 87-89):
```python
expected_total = round(subtotal_num - discount_num + tax_num, 2)
if abs(expected_total - total_num) > 0.02:
    errors.append(f"Calculated total {expected_total:.2f} != receipt total {total_num:.2f}")
```
This is the arithmetic check: it calculates what the total should be by taking the subtotal, subtracting the discount, and adding the tax, and flags an error if it doesn't match the printed total within 2 cents (to allow for small rounding differences).
