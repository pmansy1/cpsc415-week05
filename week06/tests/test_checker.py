"""No-key tests for the checker: the code that compares a critique with the requirements.

    python3 -m pytest week06/tests -v      # no key, well under a second
"""
from checker import check_checklist, disagreements, extract_json, text_matches

REQS = [
    "There is a faceless display mannequin, not a real person",
    "The mannequin wears a suit or a formal dress",
    "There is a placard beside the mannequin",
]


def critique_with(*met):
    return {"checks": [{"requirement": r, "met": m, "evidence": "seen"} for r, m in zip(REQS, met)]}


# Behavior 13: all met is ok; an unmet requirement is reported by name.
def test_all_met_is_ok():
    result = check_checklist(REQS, critique_with(True, True, True))
    assert result == {"ok": True, "problems": [], "unmet": [], "missing": [], "extra": []}


def test_unmet_requirement_is_reported_by_name():
    result = check_checklist(REQS, critique_with(True, False, True))
    assert not result["ok"]
    assert result["unmet"] == [REQS[1]]


def test_met_must_be_literally_true():
    c = critique_with(True, "yes", True)          # a string is not a boolean answer
    assert check_checklist(REQS, c)["unmet"] == [REQS[1]]


# Behavior 11: an unanswered requirement is a problem even if the rest pass.
def test_unanswered_requirement_is_a_problem():
    partial = {"checks": [{"requirement": REQS[0], "met": True}, {"requirement": REQS[2], "met": True}]}
    result = check_checklist(REQS, partial)
    assert not result["ok"]
    assert result["missing"] == [REQS[1]]
    assert result["unmet"] == []


# Behavior 12: an invented requirement is a problem.
def test_invented_requirement_is_flagged():
    c = critique_with(True, True, True)
    c["checks"].append({"requirement": "The lighting is dramatic", "met": True})
    result = check_checklist(REQS, c)
    assert not result["ok"]
    assert result["extra"] == ["The lighting is dramatic"]


# Behavior 14: requirement text is matched after normalizing case and punctuation.
def test_requirement_text_is_matched_loosely():
    c = {"checks": [{"requirement": r.upper() + ".", "met": True} for r in REQS]}
    assert check_checklist(REQS, c)["ok"]


# Behavior 9: not JSON is a failed critique, not a crash.
def test_non_json_reply_is_a_failed_critique():
    result = check_checklist(REQS, extract_json("Sorry, I cannot see the image."))
    assert not result["ok"]
    assert result["missing"] == REQS


def test_json_without_a_checks_list_is_a_failed_critique():
    result = check_checklist(REQS, {"verdict": "looks great"})
    assert not result["ok"]
    assert result["missing"] == REQS


def test_extract_json_handles_none_and_broken_json():
    assert extract_json(None) is None
    assert extract_json('{"checks": [ broken') is None
    assert extract_json("[1, 2, 3]") is None


# Behavior 10: JSON inside prose and fences is extracted.
def test_json_inside_prose_and_fences_is_extracted():
    text = 'Here is my answer:\n```json\n{"checks": [{"requirement": "a", "met": true}]}\n```\nHope that helps.'
    assert extract_json(text) == {"checks": [{"requirement": "a", "met": True}]}


# Behavior 15: expected text is compared in code.
def test_text_match_ignores_case_and_punctuation_not_letters():
    assert text_matches("WEDDING", "  wedding. ")
    assert text_matches("GAME DAY", "Game-Day")
    assert not text_matches("WEDDING", "WEDOING")
    assert not text_matches("WEDDING", "")
    assert not text_matches("WEDDING", None)


# Behavior 16: --compare reports exactly the disagreements.
def test_disagreements_between_two_critics():
    a = [{"name": "occasion-01", "critique": critique_with(True, True, True), "text_read": "WEDDING"}]
    b = [{"name": "occasion-01", "critique": critique_with(True, False, True), "text_read": "WEDOING"}]
    d = disagreements(a, b)
    assert len(d) == 1
    assert {x["requirement"] for x in d[0]["diffs"]} == {REQS[1], "<text read>"}


def test_identical_critiques_have_no_disagreements():
    a = [{"name": "occasion-01", "critique": critique_with(True, True, True), "text_read": "WEDDING"}]
    assert disagreements(a, a) == []


def test_a_requirement_only_one_critic_answered_is_a_disagreement():
    a = [{"name": "x", "critique": critique_with(True, True, True)}]
    b = [{"name": "x", "critique": {"checks": [{"requirement": REQS[0], "met": True},
                                               {"requirement": REQS[2], "met": True}]}}]
    assert [x["requirement"] for x in disagreements(a, b)[0]["diffs"]] == [REQS[1]]
