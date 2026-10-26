"""Receipt checker: deterministic arithmetic and schema verification in pure Python."""
from __future__ import annotations

import re
from typing import Any

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_receipt(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate extracted receipt data against arithmetic and schema rules.

    Returns:
        (is_valid, errors): True and empty list if valid, False and list of discrepancies otherwise.
    """
    errors: list[str] = []

    # 1. Required top-level fields
    for field in ("merchant", "total", "items"):
        if field not in data or data[field] is None:
            errors.append(f"Missing required field '{field}'")

    if not isinstance(data.get("items"), list):
        if "Missing required field 'items'" not in errors:
            errors.append("'items' must be a list")
        return False, errors

    # 2. Date format validation
    date_val = data.get("date")
    if date_val is not None:
        if not isinstance(date_val, str) or not DATE_REGEX.match(date_val):
            errors.append(f"Date '{date_val}' must be YYYY-MM-DD or null")

    # 3. Items arithmetic check
    items = data.get("items", [])
    item_sum = 0.0
    line_total_sum = 0.0

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"Item #{idx} is not a valid dictionary")
            continue

        qty = item.get("qty", item.get("quantity", 1))
        unit_price = item.get("unit_price")
        if unit_price is None:
            unit_price = item.get("price", 0.0)

        price = item.get("price", unit_price)

        try:
            qty_num = float(qty) if qty is not None else 1.0
            unit_price_num = float(unit_price) if unit_price is not None else 0.0
            price_num = float(price) if price is not None else unit_price_num

            # Normal arithmetic: qty * unit_price
            item_sum += qty_num * unit_price_num
            line_total_sum += price_num
        except (ValueError, TypeError):
            errors.append(f"Item #{idx} has invalid quantity ({qty}) or price ({unit_price})")

    subtotal_val = data.get("subtotal")
    if subtotal_val is not None:
        try:
            subtotal_num = float(subtotal_val)
            # Accept if either qty*unit_price matches subtotal OR line_total_sum matches subtotal
            if abs(item_sum - subtotal_num) > 0.02 and abs(line_total_sum - subtotal_num) > 0.02:
                errors.append(f"Item total {item_sum:.2f} != subtotal {subtotal_num:.2f}")
        except (ValueError, TypeError):
            errors.append(f"Subtotal '{subtotal_val}' is not a valid number")
            subtotal_num = item_sum
    else:
        # If no explicit subtotal, assume subtotal equals items sum
        subtotal_num = item_sum

    # 4. Total arithmetic check: subtotal - discount + tax == total
    discount_val = data.get("discount")
    tax_val = data.get("tax")
    total_val = data.get("total")

    discount_num = 0.0
    if discount_val is not None:
        try:
            # Normalize discount: if reported negative, convert to positive deduction
            discount_num = abs(float(discount_val))
        except (ValueError, TypeError):
            errors.append(f"Discount '{discount_val}' is not a valid number")

    tax_num = 0.0
    if tax_val is not None:
        try:
            tax_num = float(tax_val)
        except (ValueError, TypeError):
            errors.append(f"Tax '{tax_val}' is not a valid number")

    if total_val is not None:
        try:
            total_num = float(total_val)
            expected_total = round(subtotal_num - discount_num + tax_num, 2)
            if abs(expected_total - total_num) > 0.02:
                errors.append(
                    f"Calculated total {expected_total:.2f} != receipt total {total_num:.2f} "
                    f"(subtotal {subtotal_num:.2f} - discount {discount_num:.2f} + tax {tax_num:.2f})"
                )
        except (ValueError, TypeError):
            errors.append(f"Total '{total_val}' is not a valid number")

    return (len(errors) == 0, errors)
