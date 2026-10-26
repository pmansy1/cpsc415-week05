"""Evaluation suite comparing vision model extractions against expected.json.

Calls the vision model once per image (cached across checks) and asserts:
1. Total amount matches expected
2. Item count matches expected
3. Merchant name matches expected
4. Date matches expected (or null if missing year)
5. Checker reports no arithmetic or schema errors
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest
from receipts.checker import validate_receipt
from receipts.reader import extract_receipt

RECEIPT_DIR = Path(os.environ.get("RECEIPT_DIR", "images"))
EXPECTED_FILE = RECEIPT_DIR / "expected.json"

HAS_KEY = bool(os.environ.get("OPENROUTER_API_KEY"))

# Global session cache so that all test methods share a single model call per image
EXTRACTION_CACHE: dict[str, tuple[dict[str, Any] | None, dict[str, Any], str | None]] = {}


def get_expected_data() -> dict[str, dict[str, Any]]:
    if not EXPECTED_FILE.exists():
        return {}
    return json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))


def get_receipt_data(image_name: str) -> dict[str, Any]:
    """Retrieve extracted receipt data for an image, calling the API only once."""
    if image_name not in EXTRACTION_CACHE:
        image_path = RECEIPT_DIR / image_name
        data, usage, err = extract_receipt(image_path)
        EXTRACTION_CACHE[image_name] = (data, usage, err)

    data, usage, err = EXTRACTION_CACHE[image_name]
    if err:
        pytest.fail(f"Extraction failed for {image_name}: {err}")
    assert data is not None, f"Data is None for {image_name}"
    return data


expected_dict = get_expected_data()
receipt_keys = list(expected_dict.keys())


@pytest.mark.skipif(not HAS_KEY, reason="OPENROUTER_API_KEY not set")
class TestReceiptEval:
    @pytest.mark.parametrize("image_name", receipt_keys)
    def test_merchant(self, image_name: str):
        data = get_receipt_data(image_name)
        expected = expected_dict[image_name]["merchant"]
        actual = data.get("merchant", "")
        exp_words = set(re.findall(r"\w+", expected.lower()))
        act_words = set(re.findall(r"\w+", actual.lower()))
        assert (
            exp_words.issubset(act_words)
            or act_words.issubset(exp_words)
            or expected.lower() in actual.lower()
            or actual.lower() in expected.lower()
        ), f"Expected merchant '{expected}', got '{actual}'"

    @pytest.mark.parametrize("image_name", receipt_keys)
    def test_date(self, image_name: str):
        data = get_receipt_data(image_name)
        expected = expected_dict[image_name]["date"]
        actual = data.get("date")
        assert actual == expected, f"Expected date '{expected}', got '{actual}'"

    @pytest.mark.parametrize("image_name", receipt_keys)
    def test_items_count(self, image_name: str):
        data = get_receipt_data(image_name)
        expected = expected_dict[image_name]["items"]
        actual = len(data.get("items", []))
        assert actual == expected, f"Expected {expected} items, got {actual}"

    @pytest.mark.parametrize("image_name", receipt_keys)
    def test_total(self, image_name: str):
        data = get_receipt_data(image_name)
        expected = float(expected_dict[image_name]["total"])
        actual = float(data.get("total", 0.0))
        assert abs(actual - expected) <= 0.02, f"Expected total {expected}, got {actual}"

    @pytest.mark.parametrize("image_name", receipt_keys)
    def test_checker_validity(self, image_name: str):
        data = get_receipt_data(image_name)
        is_valid, errors = validate_receipt(data)
        assert is_valid is True, f"Checker reported errors for {image_name}: {errors}"
