#!/usr/bin/env python3
"""CLI utility to extract structured data from a receipt image and validate arithmetic."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from receipts.checker import validate_receipt
from receipts.reader import extract_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract structured receipt data using vision models.")
    parser.add_argument("image", type=str, help="Path to receipt image file")
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model slug on OpenRouter (default: env CHAT_MODEL or minimax/minimax-m3)",
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}", file=sys.stderr)
        return 1

    model_name = args.model or os.environ.get("CHAT_MODEL", "minimax/minimax-m3")

    data, usage, error = extract_receipt(image_path, model=model_name)
    if error:
        print(f"Extraction failed: {error}", file=sys.stderr)
        return 1

    # Output formatted JSON
    print(json.dumps(data, indent=2))

    # Run deterministic code checker
    is_valid, errors = validate_receipt(data)
    if is_valid:
        print("CHECK: ok")
    else:
        print(f"CHECK: failed with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")

    # Usage line
    prompt_toks = usage.get("prompt_tokens", 0)
    compl_toks = usage.get("completion_tokens", 0)
    print(f"[{model_name} · {prompt_toks} in / {compl_toks} out]")

    return 0 if is_valid else 2


if __name__ == "__main__":
    sys.exit(main())
