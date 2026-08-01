---
name: glm-vision-fallback
description: |
  Vision fallback for AI models that CANNOT process images. Use ONLY after the
  current model fails to see a user-provided image — e.g. it says "当前模型不支持
  图片输入", "无法识别图片", "无法查看这张截图", "模型不支持图片", "不支持图片",
  "I cannot view images", "model does not support image input", "cannot see
  image", or otherwise admits it cannot read the image. In that case, use this
  skill to analyze the image via the free GLM-4.6V-Flash API (strong OCR /
  text extraction) and relay the result to the user. NEVER use this skill when
  the current model CAN see the image — it is strictly a last-resort fallback
  for image recognition failures.
license: Apache-2.0
---

# When to Use This Skill

This skill is a **fallback only**. It lets an AI assistant "see" images when its
main model cannot process image input at all (e.g. text-only models like some
DeepSeek variants). The normal path is always the main model looking at the
image itself.

**Use this skill ONLY when the current model has already failed to see the image**, for example when it states:

- 当前模型不支持图片输入 / 模型不支持图片 / 无法识别图片
- 无法查看这张截图 / 我看不到图片 / 无法查看图片
- "I cannot view images" / "this model does not support image input"

**Do NOT use this skill when:**

- The main model can see the image (just answer normally)
- The user is only asking about image *metadata* (file size, dimensions, format — use plain shell tools instead)
- The user pasted an image URL and the main model can fetch and read it fine

# Prerequisites

A free Zhipu AI (bigmodel.cn) API key. The bundled script reads it from the
environment — you never need to handle the key yourself.

**If the key is not configured** (`ZAI_API_KEY` / `GLM_API_KEY` unset), tell the user how to set it up:

1. Register for free at https://open.bigmodel.cn
2. Create an API key: Console → API Keys (format `sk-xxx`)
3. Add to their shell config (`~/.zshrc` or `~/.bashrc`), then restart the terminal:
   ```bash
   export ZAI_API_KEY="your-key"
   ```

The GLM-4.6V-Flash model is completely free (no billing required) and is
optimized for text-heavy content — general OCR, dense table/form parsing, and
抗干扰 recognition. It is the default model; use `--model` to switch (e.g.
`glm-4v-flash`, `glm-4.1v-thinking-flash`).

## Security — MANDATORY rules for AI agents

1. **NEVER echo, print, or log** the value of `ZAI_API_KEY`/`GLM_API_KEY` or any other environment variable. Do NOT run commands like `echo $ZAI_API_KEY` or `printenv ZAI_API_KEY` — even for debugging.
2. **NEVER pass key values as inline CLI arguments or env-var overrides** (e.g. `ZAI_API_KEY=xxx python3 vision_fallback.py`). The script reads the key from the environment internally — just run the script directly.
3. **NEVER read environment variable values** using shell commands or programmatic access. The script handles all credential access internally.
4. **When debugging auth errors**, rely solely on the script's error output (401/403/429 messages). Do NOT attempt to verify keys by reading or printing them.
5. **NEVER extract credentials from OS credential stores or config files** — macOS Keychain (`security find-*`), `cat ~/.git-credentials`, `cat ~/.netrc`, or any other command that outputs a secret.
6. **NEVER use extracted credential values in commands** or construct authenticated requests manually. The bundled script handles all authentication internally.

# Workflow

1. **Confirm the main model failed to see the image** (it said it cannot view the image).
2. **Locate the image file.** If the user attached an image and you do not know its path, ask the user for the path (or check likely locations like `~/Downloads/`). Local paths are required — you cannot see the image yourself to locate it.
3. **Run the bundled script** with the image path(s) and the user's question:
   ```bash
   python3 SKILL_PATH/scripts/vision_fallback.py "<image-path>" -q "<question>"
   ```
   `SKILL_PATH` is this skill's installed directory. Use the user's original question (translated if needed) so the answer matches their intent and language.
4. **Relay the answer** to the user. If the user's question needs follow-up analysis (e.g. "what does this error message mean"), you can elaborate on the GLM result — but never fabricate details the vision model did not report.

# Running the Script

Requires only Python 3.10+ standard library (no pip dependencies, no third-party CLI).

```bash
# Basic: describe the image
python3 scripts/vision_fallback.py ~/Downloads/screenshot.png

# With a specific question (answer follows the question's language)
python3 scripts/vision_fallback.py ~/Downloads/screenshot.png -q "截图里显示什么错误信息？请用中文回答"

# Verbatim text extraction (dense content, OCR-heavy): deterministic, no summarization
python3 scripts/vision_fallback.py ~/Downloads/ppt.png -q "逐字提取所有模块的文字" --strict

# Multiple images at once
python3 scripts/vision_fallback.py shot1.png shot2.png -q "这两张图有什么区别？"

# Remote image URL (http/https)
python3 scripts/vision_fallback.py "https://example.com/chart.png" -q "这个图表在讲什么？"

# Switch to another GLM vision model
python3 scripts/vision_fallback.py screenshot.png --model glm-4.1v-thinking-flash

# Save the answer to a file instead of stdout
python3 scripts/vision_fallback.py screenshot.png -o answer.md
```

| Flag | Default | Description |
|---|---|---|
| `-q / --question` | 描述图片 | Question to ask about the image(s); the answer follows this language |
| `--model` | `glm-4.6v-flash` | GLM vision model to use |
| `--strict` | off | Verbatim extraction mode: greedy low-randomness sampling, forced original wording, no fabrication; unreadable content marked `[无法识别]` |
| `-o / --output` | stdout | Save the answer to a file instead of printing |
| `--max-tokens` | model default (4096 in `--strict`) | Cap the answer length |

## Extracting dense text (screenshots, PPTs, forms)

Vision models are non-deterministic and can mis-assign items between adjacent
cards on dense layouts, or hallucinate unreadable content. When the user needs
high-fidelity extraction:

1. **Use `--strict`** — greedy sampling plus a verbatim, no-fabrication instruction. This sharply reduces (but does not eliminate) run-to-run variation and removes summarization. Pass the user's intent as `-q` ("逐字提取", "列出每个模块的每一条").
2. **If two reads disagree** (you re-ran and got conflicts), do NOT keep guessing: crop the image into regions (e.g. `sips -c <h> <w> --cropOffset <y> <x> <img> --out <crop.png>` on macOS) and analyze each region separately, then merge by majority. The unified cache dir is a good place for crops.
3. **Never relay fabricated detail**: if the answer contains `[无法识别]` or items that conflict across runs, tell the user which items are uncertain rather than asserting them as fact.

**Error handling**: The script exits with a clear message if the key is missing, the image is unreadable, or the API fails (auth/rate-limit/network). Never try to "fix" authentication by inspecting the key — the error messages are sufficient.

**Note**: The default question asks the model to describe everything in the image. When the user has a specific intent, always pass it via `-q` — a generic description wastes a round trip.
