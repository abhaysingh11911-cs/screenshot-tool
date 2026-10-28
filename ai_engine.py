import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

ALLOWED_TOOLS = {"blur", "rectangle", "circle", "highlight", "arrow", "text", "number"}

PROMPT_TEMPLATE = """You are the decision engine of a screenshot annotation tool.
The screenshot is __W__ x __H__ pixels. OCR found these words, one per line as:
text|left|top|width|height (pixels, origin at top-left):
__WORDS__

User request: __REQUEST__

Reply with JSON only, in exactly this shape:
{"actions": [{"tool": "blur", "x": 0, "y": 0, "w": 0, "h": 0, "text": "", "color": ""}]}

Rules:
- tool must be one of: blur, rectangle, circle, highlight, arrow, text, number
- x, y, w, h is a box in screenshot pixels around the target. If the target spans several OCR words (like a full email address or a sentence), merge them into one box.
- color is one of red, green, blue, yellow, black, white, or empty for the default
- text is only used when the tool is text
- If the request cannot be done with these tools, or the target is not in the OCR words, reply {"actions": []}
"""


class AIError(Exception):
    pass


def _clean(actions, width, height):
    cleaned = []
    for a in actions:
        if not isinstance(a, dict):
            continue
        tool = str(a.get("tool", "")).lower()
        if tool not in ALLOWED_TOOLS:
            continue
        try:
            x, y = int(a.get("x", 0)), int(a.get("y", 0))
            w, h = int(a.get("w", 0)), int(a.get("h", 0))
        except (TypeError, ValueError):
            continue
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))
        cleaned.append({
            "tool": tool, "x": x, "y": y, "w": w, "h": h,
            "text": str(a.get("text", "")),
            "color": str(a.get("color", "")).lower(),
        })
    return cleaned


def get_actions(user_prompt, ocr_items, width, height):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise AIError("GEMINI_API_KEY not found in the .env file")

    words = "\n".join(
        f"{i['text']}|{i['left']}|{i['top']}|{i['width']}|{i['height']}"
        for i in ocr_items[:500]
    )
    prompt = (PROMPT_TEMPLATE
              .replace("__W__", str(width)).replace("__H__", str(height))
              .replace("__WORDS__", words).replace("__REQUEST__", user_prompt))

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", temperature=0),
        )
    except Exception as e:
        raise AIError(f"AI request failed: {e}")

    try:
        data = json.loads(response.text or "{}")
    except json.JSONDecodeError:
        raise AIError("AI returned a reply the app could not read")

    actions = data.get("actions", []) if isinstance(data, dict) else data
    return _clean(actions, width, height)