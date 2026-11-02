# Intent: Image set (FitLab occasions)

## Goal
Generate five outfit images from one prompt family, have a vision model answer a yes/no checklist about each image, and check those answers in plain code, so that a wrong or sloppy critique is visible instead of trusted. The prompt family is the one FitLab (Team Project 1) needs: the same faceless mannequin in the same studio, dressed for five different occasions, with a small placard naming the occasion.

## Who it is for
- **FitLab's critique path.** FitLab already asks a vision model to score outfits. Today nothing outside that model checks whether the model answered the question it was asked. This lab builds that check.
- **Me, for the Comprehension Defense:** I can show what a seed does and why a critique has to be checked by something other than the critic.

## Constraints
- **Language:** Python 3, the same as my Week 5 receipt reader and FitLab's backend.
- **Image model:** `black-forest-labs/flux.2-klein-4b` through OpenRouter's Image API, with one comparison model, `google/gemini-3.1-flash-lite-image`, run on a single prompt.
- **Vision models:** `minimax/minimax-m3` critiques. `xiaomi/mimo-v2.6-flash` checks the critic by answering the same checklist.
- **Prompt family:** five occasions (wedding, hike, job interview, game day, beach). Each image has a faceless grey mannequin, a plain light-grey studio, and a white placard reading the occasion in capital letters. Only the occasion and its outfit change.
- **Fixed seeds** (601–605). One generation per prompt, one critique per image. No model call inside a test loop.
- **Requirements are yes/no questions a person can answer by looking.** The placard text is compared **in code**, not by the critic.
- **Cost ceiling:** $0.50 for the whole lab, including the comparison model and the second critic.
- **No API key in the repository.** It comes from `OPENROUTER_API_KEY`.

## Not in scope
- Scoring how fashionable an outfit is. The checklist asks only what is visibly there.
- Changing FitLab's existing 0–100 critique. The team-repo PR adds the checklist checker beside it.
- Hosting or deployment (Week 7).

## Success looks like
1. `week06/images/` holds five images and a `manifest.json` that records the prompt, seed, model, media type and the cost from each reply.
2. The no-key tests pass in under a second and cover: all met; one unmet, named; one unanswered; one invented; not JSON; JSON inside prose; the placard text compared in code (`"WEDDING"` against `"WEDOING"` is a mismatch).
3. `CHECKS.md` records where the two critics disagreed, what I saw in each image, and which check caught what.

## Open questions
None.

## Corrections made to agent draft
1. The draft's prompt family was five colorways of one outfit. I changed it to **five occasions**, because that matches FitLab's brief-to-outfit flow and gives each image a different word to read.
2. The draft let the critic report the placard text as one of the checklist answers. I moved that to a **separate narrow question whose answer the code compares** with the expected text, because the critic grading its own read is exactly the October 19 failure.

**Approved by:** Patrick Manswell, November 2, 2026
