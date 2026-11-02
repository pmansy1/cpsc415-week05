# Week 6 checks: image set, critique checked, reviewed PR

All runs on 2026-11-02 from `week06/`. The costs are the `usage.cost` values from each reply, as recorded in the manifests and critique files.

## 1. No-key tests and linter

| Check | Command | Result |
|---|---|---|
| Checker and CLI tests, no key | `env -u OPENROUTER_API_KEY python3 -m pytest week06/tests -q` | **17 passed** in 0.44 s |
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

This is under the plan's $0.13–0.15 estimate and the intent's $0.50 ceiling. The PR reviewer's cost is in the Review section.

## 7. Review

*(Filled in after the pull request in the team repository; see below.)*
