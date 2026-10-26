"""Receipt reader: OpenRouter multimodal vision caller and robust JSON extractor."""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = """You are an expert receipt OCR and structured data extractor.
Read the receipt image and extract the data into a single, valid JSON object with this exact shape:
{
  "merchant": string,
  "date": "YYYY-MM-DD" or null if year is missing or unprinted,
  "currency": "USD",
  "items": [
    {"name": string, "qty": number, "unit_price": number, "price": number}
  ],
  "subtotal": number,
  "discount": number or null,
  "tax": number or null,
  "total": number
}

Rules:
1. "merchant": The business or organization name printed on the receipt.
2. "date": ISO format "YYYY-MM-DD". If the year is NOT printed (e.g., 'Oct 3' without a year), set "date" to null. NEVER guess or invent a year.
3. "items": List of all items purchased.
   - "name": Item description.
   - "qty": Item quantity (e.g. 1, 2, 3).
   - "unit_price" and "price": The individual price per single unit, so that qty * unit_price equals the item line total. If the receipt prints a line total for multiple items (e.g., "3 x Cookies 3.00" or "2 x Blue book 2.50 @ 1.25 ea"), use the per-unit price (1.00, 1.25) so that the arithmetic qty * unit_price adds up to the subtotal.
4. "subtotal": The subtotal before discount/tax. If not explicitly labeled, calculate sum of items.
5. "discount": Positive number if a discount was applied, or null if none.
6. "tax": Sales tax amount, or null if none.
7. "total": The final total amount charged.
8. Output ONLY the JSON object. Do not wrap in conversational text.
"""


def encode_image(image_path: Path | str) -> str:
    """Encode an image file to a base64 data URL."""
    path = Path(image_path)
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = "image/png"
    encoded_bytes = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded_bytes}"


def parse_model_response(raw_text: str) -> dict[str, Any]:
    """Extract and parse JSON from a model response string.

    Handles:
    - Pure JSON strings
    - Markdown fenced blocks (```json ... ```)
    - Surrounding conversational prose
    Raises ValueError if no valid JSON object can be extracted.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("No valid JSON found in model response: response is empty")

    text = raw_text.strip()

    # 1. Try direct parsing
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 2. Try markdown fence extraction
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match:
        try:
            data = json.loads(fenced_match.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 3. Find outermost matching curly braces
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidate = text[start_idx : end_idx + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in model response:\n{raw_text[:200]}")


def extract_receipt(
    image_path: Path | str,
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any], str | None]:
    """Send receipt image to OpenRouter multimodal vision model and return parsed data.

    Returns:
        (data, usage, error):
        - data: parsed receipt dict or None on failure
        - usage: usage token metadata dict
        - error: error message string or None on success
    """
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, {}, "Missing OPENROUTER_API_KEY environment variable"

    chosen_model = model or os.environ.get("CHAT_MODEL", "minimax/minimax-m3")

    try:
        data_url = encode_image(image_path)
    except Exception as exc:
        return None, {}, f"Failed to read/encode image: {exc}"

    body: dict[str, Any] = {
        "model": chosen_model,
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all data from this receipt as JSON."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    }

    # Model specific knob: xiaomi/mimo-v2.6-flash requires reasoning disabled
    # to avoid exhausting output budget in hidden thinking loops.
    # minimax/minimax-m3 benefits from reasoning enabled to read faded dates.
    if "xiaomi" in chosen_model or "mimo" in chosen_model:
        body["reasoning"] = {"enabled": False}

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/pmansy1/cpsc415-week05",
        "X-Title": "CPSC415 Week 5 Receipt Reader",
    }

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode("utf-8", errors="replace")
        return None, {}, f"HTTP {http_err.code} from OpenRouter: {err_body}"
    except Exception as exc:
        return None, {}, f"Network error during OpenRouter request: {exc}"

    choices = resp_data.get("choices", [])
    if not choices:
        return None, resp_data.get("usage", {}), "OpenRouter returned empty choices list"

    raw_content = choices[0].get("message", {}).get("content", "")
    usage = resp_data.get("usage", {})

    try:
        parsed_json = parse_model_response(raw_content)
        return parsed_json, usage, None
    except ValueError as val_err:
        return None, usage, f"Failed to parse JSON from model response: {val_err}"
