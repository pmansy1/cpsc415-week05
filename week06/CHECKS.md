# Week 6 checks: image set, critique checked, reviewed PR

All runs on 2026-11-02 from `week06/`. The costs are the `usage.cost` values from each reply, as recorded in the manifests and critique files.

## 1. No-key tests and linter

| Check | Command | Result |
|---|---|---|
| Checker and CLI tests, no key | `env -u OPENROUTER_API_KEY python3 -m pytest week06/tests -q` | **18 passed** in 0.40 s (17 at first; 1 added after the PR review found the non-dict case) |
| Tests failed before the code existed | same command, before `checker.py` (commit `Image set: failing checker tests`) | collection error: `No module named 'checker'`. Then 3 CLI tests failed before `generate.py` / `critique.py` existed |
| Linter | `ruff check .` (whole repository) | **No findings** ("All checks passed!"), both before and after the Week 6 code |

**Guard finding (Week 5 hook, not changed).** The lab expects `pip install openrouter` to be blocked until `spec.md` names it. It was **not** blocked (exit 0): `guard.py` checks whether the package name appears *anywhere* in `spec.md`, and "OpenRouter API" and `OPENROUTER_API_KEY` were already there from Week 5. The guard matches a substring, not a Dependencies entry. I left the hook unchanged and named `openrouter` under Week 6 dependencies anyway. A stricter guard would read only the Dependencies section.

## 2. The image set: FLUX.2 klein, five occasions

Model `black-forest-labs/flux.2-klein-4b`, aspect ratio 3:4, `image/jpeg`, 1024×1376. I looked at every image at full size **before** reading the critiques. The "My eyes" column was written first. The critic columns are `minimax/minimax-m3`.

| Image | Seed | Cost | Seconds | Checker (m3 checklist) | Placard expected → m3 read | My eyes |
|---|---|---|---|---|---|---|
| occasion-01 wedding | 601 | $0.015 | 11.0 | ok | WEDDING → `WEDDING` ✓ | All 4 met. But **two mannequins** (the prompt asked for one), and they are **fused at the shoulder**. No requirement covers either |
| occasion-02 hike | 602 | $0.015 | 3.9 | ok | HIKE → `HIIKE` **MISMATCH** | All 4 met. **Placard misspelled "HIIKE"** (confirmed at full size). A spare pair of boots on the floor |
| occasion-03 interview | 603 | $0.015 | 3.8 | ok | INTERVIEW → `INTERVIEW` ✓ | All 4 met |
| occasion-04 game day | 604 | $0.015 | 9.3 | ok | GAME DAY → `GAME DAY` ✓ | All 4 met |
| occasion-05 beach | 605 | $0.015 | 10.3 | ok | BEACH → `BEACH` ✓ | All 4 met. I first thought the sandals were on the floor; at full size they are on the feet |

**Generation total: $0.075.** **m3 critique total (five checklists plus five placard reads): $0.00616.** The code's verdict was 4/5 pass; occasion-02 fails on the placard text.

## 3. Seed check: occasion-02, seed 602, same model, generated again

| Question | Answer |
|---|---|
| Same picture? | **Almost.** Same mannequin, jacket, backpack, trousers, boots, placard position, and the same **"HIIKE"** misspelling. The spare boots on the floor are arranged differently (side by side vs stacked). |
| Same bytes? | **No.** `cmp`: `differ: char 24, line 1`. Sizes 286,803 vs 288,652 bytes. SHA-1 `2749bbf…` vs `292c0fe…`. |
| Pixel difference | Mean absolute difference 2.7 / 255, max 242 (the moved boots). |
| Cost | $0.015, 4.0 s |

**What the seed means for this model:** the same model, prompt and seed reproduce the composition and even the spelling mistake, but not identical pixels or bytes. Compare by looking, or by the placard read, never by hashing the file. A different seed is the way to get a different picture of the same brief.

## 4. Comparison image model: `google/gemini-3.1-flash-lite-image`, occasion-02, seed 602

| | FLUX.2 klein | Gemini 3.1 flash-lite image |
|---|---|---|
| Cost (`usage.cost`) | $0.015 | **$0.03362** (about 2.2×) |
| Seconds | 3.9 | 10.7 |
| Size | 1024×1376 | 896×1200 |
| Placard | `HIIKE` ✗ | **`HIKE` ✓** (m3 read and my eyes) |
| Requirements (m3 checklist + my eyes) | 4/4 met | 4/4 met, one pair of boots, worn |
| m3 critique cost | $0.00124 | $0.00099 |

Gemini spelled the word right where FLUX misspelled it with the same seed. That is one sample, not a rule, but it is the text failure the placard read exists for. FitLab already uses the Gemini image family for generation.

## 5. The critic checked

### Second model: `xiaomi/mimo-v2.6-flash` (reasoning off)

`python3 critique.py --compare critique.json critique-mimo.json` → **0 image(s) where the two critics disagree.** Both said every requirement was met on all five images, and both read the same five placard texts, including `HIIKE`. mimo cost **$0.00191** for all five, about a third of m3's $0.00616.

Agreement is not correctness, so I read every `evidence` sentence:

| Image | Requirement | m3 said | mimo said | What I saw |
|---|---|---|---|---|
| occasion-02 | placard on a stand (met: both true) | evidence: *"A white **HIKE** placard is mounted on a stand"* | evidence: *"reads 'HIIKE' rather than 'HIKE'"* | It reads **HIIKE**. Inside its checklist, m3 **silently corrected the spelling**, even though its own narrow placard read said `HIIKE` |
| occasion-01 | faceless mannequin (met: both true) | "two faceless grey mannequins" | "two identical grey, faceless figures" | True. Both noticed two mannequins, but neither mentioned that they are **fused together**; the checklist didn't ask |
| occasion-02 | wears hiking boots | "on the mannequin's feet" | "on the mannequin's feet (and a spare pair sits beside them)" | True; mimo was more complete |

No verdict disagreements, so there was nothing for `--compare` to flag. The one real error, the misspelled placard, was caught only by the **narrow question compared in code**.

### Open-ended critique: m3, occasion-01, "Critique this outfit image. What is wrong with it?"

A single standalone call with no checklist and no prompt context. The agent ran it as a one-off script outside `critique.py`, not in my own terminal; the request had no spec or system prompt. Cost **$0.00117**, 2040 in / 455 out.

| Claim | True? |
|---|---|
| Two mannequins, styled as a wedding look | **True.** But it treated two mannequins as intended ("groom and groomsman"); it doesn't know the prompt asked for one |
| Brown shoes "clash noticeably" with navy suits; navy "conventionally" takes black | **False as a fact.** Navy with brown shoes is a standard pairing. This is an opinion stated as a rule |
| No boutonnières or pocket squares | True (none visible). Not a defect against our brief |
| Light blue ties are "somewhat casual" | Opinion |
| "Both ties appear slightly short" | **Unsupported.** The ties disappear under the buttoned jackets, so their length can't be seen |
| Shirt cuffs "hard to tell" | Hedged. The white cuffs are visible below the sleeves |
| Hands poorly articulated, looks like a costume display | Partly true: plain display-mannequin hands. Matches the prompt ("display mannequin") |
| Fused mannequins, wrong mannequin count, placard | **Not mentioned.** The one visible generation defect went unnoticed |

It made 7 claims: 2 true, 1 false, 1 unsupported, and the rest opinion or hedged. It missed the actual defect. It reads confident and specific, which is exactly what makes it dangerous as a verdict.

### Which check caught what, and which goes into FitLab

The **narrow question compared in code** was the only check that caught the real text error ("HIIKE"). Both critics marked the checklist "met", and m3's own evidence even quietly corrected the word to "HIKE". The **second model** caught nothing new this run because both critics agreed, though mimo's evidence was more accurate than m3's on the placard. Only **a person looking** saw that the wedding mannequins are fused together, because no check asked and the open-ended critique talked about shoes instead. For FitLab's critique path I would add the **narrow read compared in code** for any text the brief asks for, and keep **a person looking** at anything flagged. The second model is worth its third of the cost as a cross-check, but it is not a substitute for asking a narrower question.

## 6. Cost of the whole lab

| Part | Cost |
|---|---|
| Five FLUX images | $0.07500 |
| Seed re-run (FLUX, 1 image) | $0.01500 |
| Comparison image (Gemini flash-lite, 1 image) | $0.03362 |
| m3 critiques (5) + Gemini image critique (1) | $0.00715 |
| mimo critiques (5) | $0.00191 |
| Open-ended critique (1) | $0.00117 |
| **Total for the image set** | **$0.13385** |
| PR reviewer, 8 runs | $0.03936 |
| **Total for the lab** | **$0.17321** |

This is under the plan's $0.13–0.15 estimate and the intent's $0.50 ceiling. The PR reviewer's cost is in the Review section.

## 7. Review

**PR:** https://github.com/Gabbykoms/fitlab/pull/8, branch `week06-patrick` → `main` in `Gabbykoms/fitlab`.

**What the PR carries:**
- `checklist.py`: this lab's checker, in FitLab's style.
- `eval.py --imageset`: the checklist and placard read through FitLab's existing `provider.vision`, compared across the first two models.
- `imagesets/patrick-occasions/`: these five images, with `prompts.json`, `manifest.json` and `imagesets/generate.py`.
- Spec section **11**, the Week 5 guard (`.claude/hooks/guard.py` + `settings.json`), and `requirements.txt` with `openrouter` and `ruff`.

**Tests before code:** `a3b556e` spec → `cbbd839` failing tests (`No module named 'checklist'`) → `370a647` implementation. Every later fix also started from a failing test.

**Gate (`gate.sh` as `pre-push`):**
- The first push was **stopped**: 2 failed, 127 passed. My async tests clashed with Playwright's event loop when run in the full suite (they passed alone). I fixed it with FitLab's `tests/fakes.run_async`.
- Every later push passed: ruff clean, 129–133 passed.
- `main` had 19 ruff errors in teammates' files before this PR. I fixed them in a separate commit (`88c2f2e`), flagged in the PR description, because the gate can't pass otherwise.

**Reviewer runs** (`examples/pr-review/review.py --base origin/main`, logs in `week06/review/`):

| Run | Commit | Model | Exit | Cost |
|---|---|---|---|---|
| 1 | 5f62295 | minimax/minimax-m3 | **2**: empty reply, 1,999 of 2,000 output tokens spent on hidden reasoning (39k-token input) | $0.01433 |
| 2 | 5f62295 | minimax/minimax-m3 | **2**: same | $0.00457 |
| 3 | 5f62295 | xiaomi/mimo-v2.6-flash | **1** | $0.00465 |
| 4 | e3b9688 | mimo | **2**: found nothing but wrote "PASS" instead of "NONE" | $0.00462 |
| 5 | e3b9688 | mimo | **0** | $0.00022 |
| 6 | 4a52c3c | mimo | 1 | $0.00163 |
| 7 | fa0fb4c | mimo | 1 | $0.00464 |
| 8 | 1e39555 | mimo | **1**, last run | $0.00469 |

**Reviewer total: $0.0394.**

**Findings by pass, and what I did:**
- **Pass 1** (4 across runs):
  - "README claims unverifiable": wrong category, since the images are in the diff. Reworded to "open the images to verify".
  - "Spec silently changed to match the code" (raised 3 times): **pushed back**. The commit order (`a3b556e` before `cbbd839` and `370a647`) is in the PR. I added the named sign-off line, and found the reviewer had missed that my section was numbered **8**, colliding with the existing Section 8. Renumbered to **11**.
  - "`disagreements(*per_model)` raises `TypeError` with one model": **false**, because the conditional prevents the call. Proved with a test (`1e39555`).
- **Pass 2** (6 across runs):
  - `generate.py` broad except: **partly real**. Printing `{exc}` could leak a provider error body (against FitLab's CLAUDE.md). It now prints only the type and HTTP status, and `--out` is required.
  - "H-1 relies on `configured()`" (raised twice): **pushed back**, then settled with a test against the real `OpenRouter` class (`fa0fb4c`).
  - "Key-check ordering": the finding itself says "which is fine".
  - "`entry['name']` / manifest without `requirements` → `KeyError`": **pushed back**. Our own scripts write those files; they aren't model output.
- **Pass 3:**
  - `check_checklist` on a non-dict critique raised `AttributeError`: **real, fixed test-first** in both FitLab (`4a52c3c`) and this repo.
  - Only the first two models compared: now reported (`compared_models`).
  - `pytest.raises`: done.
  - Weather refactor out of scope: answered (the gate needed it).
  - "Malformed entries let a critic pass": false, because they show up as missing.
- **Pass 4:**
  - Manifest vs prompts drift: documented.
  - "Blank lines trip ruff": false.
  - "`\\` in docstring": false.

**Last exit code: 1** (run 8). Every pass-1 and pass-2 finding in it is answered on the PR. I stopped rerunning there: the reviewer is non-deterministic, and each run raised new findings, most of them false or self-contradicting (run 7's pass-2 finding concedes "which is fine"). Rerunning until a random draw exits 0 would treat the exit code as the verdict, which is what `REVIEW.md` says it isn't.

**What the gate catches that `REVIEW.md` can't:** the gate *runs* the code. My event-loop clash only appeared when the full suite ran, and no reader of the diff, human or model, flagged it. `REVIEW.md` is read by a model that sees only the diff, and it was confidently wrong several times above.

**Approved by:** *pending.* Waiting on Gabriel or Nadia to approve on GitHub. Not merged yet.
