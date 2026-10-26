"""Offline unit tests for receipt checker and JSON parser.

These tests run without an API key, without network access, and complete in <0.2 seconds.
"""
import pytest
from receipts.checker import validate_receipt
from receipts.reader import parse_model_response


def test_valid_receipt():
    data = {
        "merchant": "Mather Dining Hall",
        "date": "2026-10-02",
        "items": [
            {"name": "Chicken wrap", "qty": 1, "price": 7.49},
            {"name": "Chips", "qty": 1, "price": 1.99},
            {"name": "Drink", "qty": 1, "price": 3.36},
        ],
        "subtotal": 12.84,
        "discount": 0.0,
        "tax": 0.82,
        "total": 13.66,
    }
    is_valid, errors = validate_receipt(data)
    assert is_valid is True
    assert errors == []


def test_subtotal_mismatch():
    data = {
        "merchant": "Campus Store",
        "date": "2026-10-01",
        "items": [
            {"name": "Notebook", "qty": 2, "price": 3.00},  # sum = 6.00
            {"name": "Pen", "qty": 1, "price": 2.00},       # sum = 2.00 -> total 8.00
        ],
        "subtotal": 10.00,  # deliberately wrong
        "discount": 0.0,
        "tax": 0.50,
        "total": 10.50,
    }
    is_valid, errors = validate_receipt(data)
    assert is_valid is False
    assert any("Item total 8.00 != subtotal 10.00" in e for e in errors)


def test_total_mismatch():
    data = {
        "merchant": "Dining Hall",
        "date": "2026-10-02",
        "items": [{"name": "Meal", "qty": 1, "price": 10.00}],
        "subtotal": 10.00,
        "discount": 0.0,
        "tax": 0.80,
        "total": 12.00,  # expected 10.80
    }
    is_valid, errors = validate_receipt(data)
    assert is_valid is False
    assert any("Calculated total 10.80 != receipt total 12.00" in e for e in errors)


def test_negative_discount_normalization():
    # As noted in slides, some models extract discount as negative (-1.15)
    data = {
        "merchant": "Long Walk Coffee",
        "date": "2026-10-06",
        "items": [
            {"name": "Latte", "qty": 1, "price": 5.50},
            {"name": "Muffin", "qty": 2, "price": 3.00},
        ],
        "subtotal": 11.50,
        "discount": -1.15,
        "tax": 0.66,
        "total": 11.01,
    }
    is_valid, errors = validate_receipt(data)
    assert is_valid is True
    assert errors == []


def test_positive_discount():
    data = {
        "merchant": "Long Walk Coffee",
        "date": "2026-10-06",
        "items": [{"name": "Item", "qty": 1, "price": 10.00}],
        "subtotal": 10.00,
        "discount": 2.00,
        "tax": 0.50,
        "total": 8.50,
    }
    is_valid, errors = validate_receipt(data)
    assert is_valid is True
    assert errors == []


def test_null_date_when_year_missing():
    data = {
        "merchant": "CS Club Bake Sale",
        "date": None,
        "items": [
            {"name": "Brownie", "qty": 1, "price": 2.50},
            {"name": "Cookie", "qty": 2, "price": 2.00},
        ],
        "subtotal": 6.50,
        "discount": 0.0,
        "tax": 0.0,
        "total": 6.50,
    }
    is_valid, errors = validate_receipt(data)
    assert is_valid is True
    assert errors == []


def test_invalid_date_format():
    data = {
        "merchant": "Bake Sale",
        "date": "October 3rd",  # non-ISO format
        "items": [{"name": "Cookie", "qty": 1, "price": 2.00}],
        "subtotal": 2.00,
        "discount": 0.0,
        "tax": 0.0,
        "total": 2.00,
    }
    is_valid, errors = validate_receipt(data)
    assert is_valid is False
    assert any("Date 'October 3rd' must be YYYY-MM-DD or null" in e for e in errors)


def test_missing_required_fields():
    data = {
        "subtotal": 5.00,
        "total": 5.00,
    }
    is_valid, errors = validate_receipt(data)
    assert is_valid is False
    assert any("Missing required field 'merchant'" in e for e in errors)
    assert any("Missing required field 'items'" in e for e in errors)


def test_parse_clean_json():
    raw = '{"merchant": "Test Store", "total": 15.00, "items": []}'
    parsed = parse_model_response(raw)
    assert parsed["merchant"] == "Test Store"
    assert parsed["total"] == 15.00


def test_parse_fenced_json():
    raw = """Here is the extracted receipt data:
```json
{
  "merchant": "Trinity Bookstore",
  "total": 73.0,
  "items": []
}
```
"""
    parsed = parse_model_response(raw)
    assert parsed["merchant"] == "Trinity Bookstore"
    assert parsed["total"] == 73.0


def test_parse_prose_wrapped_json():
    raw = 'I found the following: {"merchant": "Coffee Shop", "total": 4.50, "items": []} on this receipt.'
    parsed = parse_model_response(raw)
    assert parsed["merchant"] == "Coffee Shop"
    assert parsed["total"] == 4.50


def test_parse_non_json_raises_value_error():
    raw = "I am sorry, but I cannot read this receipt because it is completely blank."
    with pytest.raises(ValueError, match="No valid JSON found in model response"):
        parse_model_response(raw)
