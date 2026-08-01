#!/usr/bin/env python3
"""Analyze images with the free GLM-4V-Flash vision model.

Fallback path for AI assistants whose main model cannot process image input.
The API key is read from the ZAI_API_KEY or GLM_API_KEY environment variable;
it is never accepted as a command-line argument.
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4.6v-flash"
ENV_KEYS = ("ZAI_API_KEY", "GLM_API_KEY")
DEFAULT_QUESTION = "请详细描述这张图片的内容，包括所有可见的文字、布局和视觉元素。"

STRICT_SYSTEM_PROMPT = """\
你是精准的图片文字提取器。必须遵守以下规则：
1. 逐字输出图中出现的所有文字，保持原文，不要概括、不要改写、不要翻译。
2. 按图中原有的分组/模块标题组织输出，条目归属严格按照文字所在区域。
3. 看不清或无法确认的内容，标注「[无法识别]」，绝对不要猜测、脑补或编造。
4. 不要输出任何图中不存在的内容。"""


def get_api_key() -> str:
    """Return the GLM API key from the environment, or exit with setup help."""
    for name in ENV_KEYS:
        value = os.environ.get(name)
        if value:
            return value
    raise SystemExit(
        "GLM-4V-Flash API key not found. Set ZAI_API_KEY or GLM_API_KEY:\n"
        "  1. Register for free at https://open.bigmodel.cn\n"
        "  2. Create an API key: Console -> API Keys (格式 sk-xxx)\n"
        "  3. Add to your shell config (~/.zshrc or ~/.bashrc):\n"
        "       export ZAI_API_KEY=\"your-key\"\n"
        "     then restart your terminal."
    )


def is_url(value: str) -> bool:
    """Return True if the value is an http(s) URL rather than a local file path."""
    return value.startswith("http://") or value.startswith("https://")


def guess_mime_type(path: Path) -> str:
    """Guess the MIME type of an image file, sniffing magic bytes when needed."""
    try:
        with open(path, "rb") as f:
            head = f.read(12)
    except OSError:
        raise ValueError(f"Cannot read image file: {path}")
    if head.startswith(b"\x89PNG"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"GIF87a") or head.startswith(b"GIF89a"):
        return "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head[:2] == b"BM":
        return "image/bmp"
    mime, _ = mimetypes.guess_type(path.name)
    if mime:
        return mime
    raise ValueError(f"Unsupported image format (cannot detect MIME type): {path}")


def encode_image_data_url(path: Path) -> str:
    """Encode a local image file as a base64 data URL for the API."""
    data = path.read_bytes()
    mime = guess_mime_type(path)
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def build_content(images: list[str], question: str) -> list[dict]:
    """Build the multimodal user message content for the chat API."""
    content: list[dict] = []
    for image in images:
        url = image if is_url(image) else encode_image_data_url(Path(image))
        content.append({"type": "image_url", "image_url": {"url": url}})
    content.append({"type": "text", "text": question})
    return content


def parse_response(data: dict) -> str:
    """Extract the answer text from a chat completions response."""
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(
            f"Unexpected API response: {json.dumps(data, ensure_ascii=False)[:500]}"
        ) from error


def _http_error_message(error: urllib.error.HTTPError) -> str:
    """Format an HTTP error from the GLM API into a readable message."""
    detail = ""
    try:
        body = json.loads(error.read().decode("utf-8"))
        error_obj = body.get("error")
        if isinstance(error_obj, dict):
            detail = error_obj.get("message", "")
        elif error_obj:
            detail = str(error_obj)
    except (json.JSONDecodeError, OSError):
        pass
    hints = {
        401: " API key is invalid or expired - check ZAI_API_KEY/GLM_API_KEY.",
        403: " access denied - check the key's permissions or account status.",
        429: " rate limited - wait a moment and retry.",
    }
    hint = hints.get(error.code, "")
    message = f"GLM vision API returned HTTP {error.code}{hint}"
    if detail:
        message += f" ({detail})"
    return message


def call_api(
    api_key: str, content: list[dict], max_tokens: int | None,
    model: str, strict: bool,
) -> str:
    """Call the GLM vision chat API and return the model's text answer."""
    if strict:
        messages = [
            {"role": "system", "content": STRICT_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ]
    else:
        messages = [{"role": "user", "content": content}]
    body: dict = {
        "model": model,
        "messages": messages,
    }
    if strict:
        body["do_sample"] = False
        body["temperature"] = 0.0
        if not max_tokens:
            max_tokens = 4096
    if max_tokens:
        body["max_tokens"] = max_tokens
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    return _post_with_retry(request)


def _post_with_retry(request: urllib.request.Request) -> str:
    """POST the request, retrying on HTTP 429 (free models rate-limit often).

    Backoff of 15s/30s/60s covers the typical flash-model rate limit window;
    other HTTP errors fail immediately with a readable message.
    """
    backoff = [15, 30, 60]
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            return parse_response(data)
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < len(backoff):
                wait = backoff[attempt]
                print(
                    f"Rate limited (HTTP 429), retrying in {wait}s...",
                    file=sys.stderr,
                )
                time.sleep(wait)
                attempt += 1
                continue
            raise RuntimeError(_http_error_message(error)) from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Network error while calling GLM vision API: {error.reason}"
            ) from error
    return parse_response(data)


def main() -> int:
    """Parse arguments, run the vision request, and print the answer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "images", nargs="+", help="image file paths or http(s) image URLs"
    )
    parser.add_argument(
        "-q", "--question", default=DEFAULT_QUESTION,
        help="question to ask about the image(s); answer follows this language",
    )
    parser.add_argument(
        "--model", default=MODEL,
        help=f"GLM vision model to use (default: {MODEL})",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="verbatim text extraction mode: deterministic, no summarization, "
        "no fabrication; unreadable content is marked [无法识别]",
    )
    parser.add_argument(
        "-o", "--output", help="save the answer to this file instead of stdout"
    )
    parser.add_argument(
        "--max-tokens", type=int, help="max output tokens (default: model default; 4096 in --strict)"
    )
    args = parser.parse_args()

    try:
        api_key = get_api_key()
        content = build_content(args.images, args.question)
        answer = call_api(api_key, content, args.max_tokens, args.model, args.strict)
    except SystemExit:
        raise
    except (ValueError, OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.output:
        Path(args.output).write_text(answer + "\n", encoding="utf-8")
        print(f"Answer saved to {args.output}")
    else:
        print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
