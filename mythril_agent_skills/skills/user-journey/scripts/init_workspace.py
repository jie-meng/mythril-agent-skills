#!/usr/bin/env python3
"""Initialize a user-journey workspace.

Creates the standard workspace layout:

    <workspace>/
    ├── JOURNEY.md
    ├── journey.json
    ├── DESIGN.md            (copied from a preset under SKILL_PATH/templates/design-styles/)
    ├── index.html           (with journey.json + design-tokens inlined)
    ├── README.md
    ├── preview.py
    └── assets/
        ├── styles.css
        ├── render.js
        └── wireframe.js

Uses only Python 3.10+ standard library — no third-party deps. Git is not
touched: if you want version control, manage it from the parent directory
that holds your journeys.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
WORKSPACE_TPL = TEMPLATES_DIR / "workspace"
DESIGN_STYLES_DIR = TEMPLATES_DIR / "design-styles"

VALID_LANGUAGES = {"en", "zh"}

# Import the canonical mermaid label-escape helper from the bundled copy
# in the same scripts/ directory. The bundled mermaid_lint.py is kept in
# sync with mythril_agent_skills/shared/mermaid/mermaid_lint.py by
# scripts/sync-shared-assets.py.
sys.path.insert(0, str(SCRIPT_DIR))
from mermaid_lint import escape_label_for_mermaid  # noqa: E402


# ---------------------------------------------------------------------------
# Pure helpers (tested in tests/skills/test_user_journey.py)
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert arbitrary text to a lowercase-hyphenated slug."""
    if not text:
        return "untitled"
    text = text.strip().lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^a-z0-9\-]+", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "untitled"


def list_design_styles(styles_dir: Path = DESIGN_STYLES_DIR) -> list[str]:
    """Return the available DESIGN.md preset slugs (without .md extension)."""
    if not styles_dir.exists():
        return []
    return sorted(p.stem for p in styles_dir.glob("*.md"))


def resolve_design_style(name: str, styles_dir: Path = DESIGN_STYLES_DIR) -> Path:
    """Resolve a design-style name to its template path. Raises if missing."""
    if not name:
        raise ValueError("design style name is required")
    candidate = styles_dir / f"{name}.md"
    if not candidate.exists():
        available = ", ".join(list_design_styles(styles_dir)) or "<none>"
        raise FileNotFoundError(
            f"design style '{name}' not found. Available: {available}"
        )
    return candidate


VALID_DEVICE_KINDS = {"mobile", "atm", "kiosk", "desktop", "tv"}

# Map the short --device-kind value to the actual screen.kind value.
DEVICE_KIND_TO_SCREEN_KIND = {
    "mobile":  "mobile-screen",
    "atm":     "atm-screen",
    "kiosk":   "kiosk-screen",
    "desktop": "desktop-window",
    "tv":      "tv-screen",
}


def build_initial_journey(
    *,
    title: str,
    subtitle: str,
    persona_name: str,
    persona_role: str,
    language: str,
    device_kind: str = "mobile",
) -> dict:
    """Build the initial journey.json structure (v3 canvas schema).

    v3 skeleton: 1 persona, 3 stages (each with one example step), and a
    starter `screens[]` array with 3 screens, plus a top-level `arrows[]`
    array wiring them together. Each device-kind seed demonstrates the
    appropriate device vocabulary (chrome + side-key-rail for ATM,
    scanner/NFC for kiosk, etc.) and the seed exercises at least two
    `screen.state` values so the user immediately sees the colored state
    cards.
    """
    if language not in VALID_LANGUAGES:
        raise ValueError(
            f"language must be one of {sorted(VALID_LANGUAGES)}, got {language!r}"
        )
    if device_kind not in VALID_DEVICE_KINDS:
        raise ValueError(
            f"device_kind must be one of {sorted(VALID_DEVICE_KINDS)}, got {device_kind!r}"
        )
    persona_slug = slugify(persona_name) or "primary-user"
    labels, summaries, step_labels = _seed_stage_strings(language)
    today = datetime.now().strftime("%Y-%m-%d")
    fallback_stage_ids = ["discover", "try", "habit"]
    stage_ids = [
        slugify(labels[idx]) if slugify(labels[idx]) != "untitled" else fallback_stage_ids[idx]
        for idx in range(3)
    ]
    fallback_step_ids = ["browse-landing", "finish-first-task", "return-to-use"]
    step_ids = [
        slugify(step_labels[idx]) if slugify(step_labels[idx]) != "untitled" else fallback_step_ids[idx]
        for idx in range(3)
    ]
    screen_ids = ["welcome", "main", "done"]
    screens, arrows = _build_seed_screens_and_arrows(
        device_kind=device_kind,
        language=language,
        title=title,
        screen_ids=screen_ids,
        stage_ids=stage_ids,
        step_labels=step_labels,
    )

    return {
        "schema_version": "3",
        "title": title,
        "subtitle": subtitle,
        "language": language,
        "personas": [
            {
                "id": persona_slug,
                "name": persona_name,
                "role": persona_role,
                "goals": [],
                "frustrations": [],
                "context": "",
            }
        ],
        "stages": [
            {
                "id": stage_ids[idx],
                "label": labels[idx],
                "summary": summaries[idx],
                "persona_id": persona_slug,
                "steps": [
                    {
                        "id": step_ids[idx],
                        "actions": [step_labels[idx]],
                        "touchpoints": [],
                        "thoughts": [],
                        "emotion": "neutral",
                        "screen_refs": [screen_ids[idx]],
                    }
                ],
                "notes": "",
            }
            for idx in range(3)
        ],
        "screens": screens,
        "arrows": arrows,
        "stickies": _seed_stickies(language),
        "metadata": {
            "created": today,
            "last_updated": today,
            "version": "0.1.0",
            "seed_device_kind": device_kind,
        },
    }


def _seed_stickies(language: str) -> list[dict]:
    """One sticky note demoing the format. Placed in the top-right of the
    canvas above the screens so users immediately see the convention."""
    if language == "zh":
        text = "便签:可以在 journey.json 的 stickies[] 里添加任意数量。"
    else:
        text = "Sticky note: add as many as you like under `stickies[]` in journey.json."
    return [
        {"id": "sticky-1", "x": 0, "y": -120, "text": text, "color": "yellow"},
    ]


def _seed_stage_strings(language: str) -> tuple[list[str], list[str], list[str]]:
    if language == "zh":
        labels = ["发现", "尝试", "习惯"]
        summaries = [
            "用户了解到产品并决定试用",
            "用户完成首次核心动作",
            "用户形成稳定使用习惯",
        ]
        step_labels = ["浏览首页", "完成首个任务", "重复使用"]
    else:
        labels = ["Discover", "Try", "Habit"]
        summaries = [
            "User learns about the product and decides to try it",
            "User completes the first core action",
            "User forms a stable usage habit",
        ]
        step_labels = ["Browse landing", "Finish first task", "Return to use again"]
    return labels, summaries, step_labels


# ---------------------------------------------------------------------------
# Per-device seed screen builders
# ---------------------------------------------------------------------------

def _build_seed_screens_and_arrows(
    *,
    device_kind: str,
    language: str,
    title: str,
    screen_ids: list[str],
    stage_ids: list[str],
    step_labels: list[str],
) -> tuple[list[dict], list[dict]]:
    """Dispatch to a per-device-kind seed factory.

    Returns ``(screens, arrows)``. Each factory builds the screens (with
    `state` set on at least one screen to demo the colored cards) plus a
    top-level arrows list connecting them.
    """
    factory = {
        "mobile":  _seed_screens_mobile,
        "atm":     _seed_screens_atm,
        "kiosk":   _seed_screens_kiosk,
        "desktop": _seed_screens_desktop,
        "tv":      _seed_screens_tv,
    }[device_kind]
    return factory(
        language=language,
        title=title,
        screen_ids=screen_ids,
        stage_ids=stage_ids,
        step_labels=step_labels,
    )


def _seed_screens_mobile(*, language, title, screen_ids, stage_ids, step_labels) -> tuple[list[dict], list[dict]]:
    s = {
        "zh": {
            "t1": "欢迎页", "t2": "主功能页", "t3": "完成页",
            "h1": "欢迎使用本产品", "h1s": "1 分钟即可完成首个任务",
            "h2": "今日任务", "h2s": "完成下方步骤即可获取奖励",
            "h3": "完成！", "h3s": "做得很棒,继续保持",
            "b_start": "开始", "b_done": "完成任务", "b_again": "再来一次",
            "tx_s": "点击开始", "tx_c": "完成任务", "tx_a": "再来一次",
        },
        "en": {
            "t1": "Welcome", "t2": "Main task", "t3": "Done",
            "h1": "Welcome to the product", "h1s": "Finish your first task in a minute",
            "h2": "Today's task", "h2s": "Complete the steps below to unlock the reward",
            "h3": "Done!", "h3s": "Nice work, keep it up",
            "b_start": "Start", "b_done": "Finish task", "b_again": "Do it again",
            "tx_s": "Tap Start", "tx_c": "Tap Finish", "tx_a": "Restart",
        },
    }[language]
    screens = [
        {
            "id": screen_ids[0], "kind": "mobile-screen", "title": s["t1"],
            "stage_id": stage_ids[0], "state": "default",
            "layout": {"type": "stack", "gap": "lg", "elements": [
                {"type": "header", "label": title},
                {"type": "spacer", "size": "md"},
                {"type": "image-placeholder", "ratio": "16:9", "label": "Hero"},
                {"type": "text", "label": s["h1"], "size": "xl", "weight": "bold"},
                {"type": "text", "label": s["h1s"], "size": "sm", "color": "secondary"},
                {"type": "spacer", "size": "md"},
                {"type": "button", "id": "start", "label": s["b_start"], "variant": "primary", "interactive": True},
            ]},
        },
        {
            "id": screen_ids[1], "kind": "mobile-screen", "title": s["t2"],
            "stage_id": stage_ids[1], "state": "default",
            "layout": {"type": "stack", "gap": "md", "elements": [
                {"type": "header", "label": s["t2"], "back": True},
                {"type": "text", "label": s["h2"], "size": "lg", "weight": "bold"},
                {"type": "text", "label": s["h2s"], "size": "sm", "color": "secondary"},
                {"type": "spacer", "size": "md"},
                {"type": "card", "title": step_labels[1], "body": "Step 1 of 1"},
                {"type": "spacer", "size": "md"},
                {"type": "button", "id": "complete", "label": s["b_done"], "variant": "primary", "interactive": True},
            ]},
        },
        {
            "id": screen_ids[2], "kind": "mobile-screen", "title": s["t3"],
            "stage_id": stage_ids[2], "state": "success",
            "layout": {"type": "stack", "gap": "lg", "elements": [
                {"type": "header", "label": s["t3"]},
                {"type": "spacer", "size": "lg"},
                {"type": "text", "label": s["h3"], "size": "xl", "weight": "bold", "color": "success"},
                {"type": "text", "label": s["h3s"], "size": "md", "color": "secondary"},
                {"type": "spacer", "size": "md"},
                {"type": "button", "id": "again", "label": s["b_again"], "variant": "secondary", "interactive": True},
            ]},
        },
    ]
    arrows = [
        {"from": f"{screen_ids[0]}#start",    "to": screen_ids[1], "label": s["tx_s"], "trigger": "tap", "kind": "default", "is_default": True},
        {"from": f"{screen_ids[1]}#complete", "to": screen_ids[2], "label": s["tx_c"], "trigger": "tap", "kind": "success", "is_default": True},
        {"from": f"{screen_ids[2]}#again",    "to": screen_ids[1], "label": s["tx_a"], "trigger": "tap", "kind": "default"},
    ]
    return screens, arrows


def _seed_screens_atm(*, language, title, screen_ids, stage_ids, step_labels) -> tuple[list[dict], list[dict]]:
    """ATM seed: chrome + side-key-rail + hardware slots, with success state on the cash-out screen."""
    s = {
        "zh": {
            "t1": "欢迎 / 插卡", "t2": "主菜单", "t3": "请取钞",
            "h1": "欢迎使用 ATM", "h1s": "请插入您的银行卡",
            "h2": "请选择业务", "h2s": "使用屏幕两侧的物理键",
            "h3": "¥200 已就绪", "h3s": "请从下方取款口取走现金",
            "k_w": "取款", "k_d": "存款", "k_b": "余额", "k_o": "其他",
            "k_t": "转账", "k_p": "缴费", "k_l": "Language", "k_e": "退卡",
            "slot_card": "插卡口", "slot_cash": "出钞口", "slot_recv": "凭条口", "slot_take": "请取钞",
            "tx_insert": "插卡", "tx_w": "取款", "tx_e": "退卡", "tx_take": "取走现金",
        },
        "en": {
            "t1": "Welcome / insert card", "t2": "Main menu", "t3": "Take cash",
            "h1": "Welcome", "h1s": "Please insert your card to begin",
            "h2": "Please select a service", "h2s": "Use the physical keys on either side",
            "h3": "$200 ready", "h3s": "Please take your cash from the slot below",
            "k_w": "Withdraw", "k_d": "Deposit", "k_b": "Balance", "k_o": "Other",
            "k_t": "Transfer", "k_p": "Pay bills", "k_l": "Language", "k_e": "Exit",
            "slot_card": "Insert card", "slot_cash": "Cash", "slot_recv": "Receipt", "slot_take": "Take cash",
            "tx_insert": "Insert card", "tx_w": "Withdraw", "tx_e": "Exit", "tx_take": "Take cash",
        },
    }[language]
    screens = [
        {
            "id": screen_ids[0], "kind": "atm-screen", "title": s["t1"],
            "stage_id": stage_ids[0], "state": "default",
            "chrome": "panel",
            "hardware": [
                {"slot": "card-reader", "position": "top", "label": s["slot_card"], "id": "h-card", "interactive": True},
                {"slot": "cash-out",    "position": "bottom", "label": s["slot_cash"]},
                {"slot": "receipt",     "position": "bottom", "label": s["slot_recv"]},
            ],
            "layout": {"type": "stack", "gap": "lg", "elements": [
                {"type": "header", "label": title},
                {"type": "text", "label": s["h1"], "size": "xl", "weight": "bold"},
                {"type": "text", "label": s["h1s"], "size": "md", "color": "secondary"},
            ]},
        },
        {
            "id": screen_ids[1], "kind": "atm-screen", "title": s["t2"],
            "stage_id": stage_ids[1], "state": "default",
            "chrome": "panel",
            "hardware": [
                {"slot": "card-reader", "position": "top", "label": s["slot_card"]},
                {"slot": "cash-out",    "position": "bottom", "label": s["slot_cash"]},
                {"slot": "receipt",     "position": "bottom", "label": s["slot_recv"]},
            ],
            "layout": {"type": "row", "justify": "between", "gap": "xl", "elements": [
                {"type": "side-key-rail", "side": "left", "gap": "lg", "keys": [
                    {"id": "k-withdraw", "label": s["k_w"], "interactive": True, "variant": "primary"},
                    {"id": "k-deposit",  "label": s["k_d"], "interactive": True},
                    {"id": "k-balance",  "label": s["k_b"], "interactive": True},
                    {"id": "k-other",    "label": s["k_o"], "interactive": True},
                ]},
                {"type": "stack", "gap": "md", "elements": [
                    {"type": "text", "label": s["h2"], "size": "lg", "weight": "bold"},
                    {"type": "text", "label": s["h2s"], "size": "sm", "color": "secondary"},
                ]},
                {"type": "side-key-rail", "side": "right", "gap": "lg", "keys": [
                    {"id": "k-transfer", "label": s["k_t"], "interactive": True},
                    {"id": "k-pay",      "label": s["k_p"], "interactive": True},
                    {"id": "k-language", "label": s["k_l"], "interactive": True},
                    {"id": "k-exit",     "label": s["k_e"], "interactive": True, "variant": "destructive"},
                ]},
            ]},
        },
        {
            "id": screen_ids[2], "kind": "atm-screen", "title": s["t3"],
            "stage_id": stage_ids[2], "state": "success",
            "chrome": "panel",
            "hardware": [
                {"slot": "cash-out", "position": "bottom", "label": s["slot_take"], "id": "h-take-cash", "interactive": True},
            ],
            "layout": {"type": "stack", "gap": "lg", "elements": [
                {"type": "header", "label": s["t3"]},
                {"type": "text", "label": s["h3"], "size": "xl", "weight": "bold", "color": "success"},
                {"type": "text", "label": s["h3s"], "size": "md", "color": "secondary"},
            ]},
        },
    ]
    arrows = [
        {"from": f"{screen_ids[0]}#h-card",       "to": screen_ids[1], "label": s["tx_insert"], "trigger": "insert-card", "kind": "default", "is_default": True},
        {"from": f"{screen_ids[1]}#k-withdraw",   "to": screen_ids[2], "label": s["tx_w"],      "trigger": "tap",         "kind": "success", "is_default": True},
        {"from": f"{screen_ids[1]}#k-exit",       "to": screen_ids[0], "label": s["tx_e"],      "trigger": "tap",         "kind": "cancel"},
        {"from": f"{screen_ids[2]}#h-take-cash",  "to": screen_ids[0], "label": s["tx_take"],   "trigger": "tap",         "kind": "default"},
    ]
    return screens, arrows


def _seed_screens_kiosk(*, language, title, screen_ids, stage_ids, step_labels) -> tuple[list[dict], list[dict]]:
    """Kiosk seed: chrome + scanner + nfc hardware demoed; success state at pay."""
    s = {
        "zh": {
            "t1": "欢迎 / 扫码", "t2": "选择商品", "t3": "确认支付",
            "h1": "请扫描商品条码", "h1s": "开始自助结账",
            "h2": "请选择购买的商品", "btn_done": "结算",
            "h3": "请使用 NFC 支付", "btn_pay": "完成支付",
            "slot_scan": "条码扫描区", "slot_nfc": "NFC 感应区",
            "tx_scan": "扫码", "tx_done": "结算", "tx_pay": "支付完成",
            "card_apple": "苹果 ¥5", "card_milk": "牛奶 ¥10", "card_bread": "面包 ¥8",
        },
        "en": {
            "t1": "Welcome / scan", "t2": "Select items", "t3": "Confirm payment",
            "h1": "Please scan item barcode", "h1s": "Start self-checkout",
            "h2": "Select items to buy", "btn_done": "Checkout",
            "h3": "Tap your phone on the NFC reader", "btn_pay": "Complete payment",
            "slot_scan": "Barcode scanner", "slot_nfc": "NFC reader",
            "tx_scan": "Scan", "tx_done": "Checkout", "tx_pay": "Paid",
            "card_apple": "Apple $1", "card_milk": "Milk $3", "card_bread": "Bread $2",
        },
    }[language]
    screens = [
        {
            "id": screen_ids[0], "kind": "kiosk-screen", "title": s["t1"],
            "stage_id": stage_ids[0], "state": "default",
            "chrome": "panel",
            "hardware": [
                {"slot": "scanner", "position": "bottom", "label": s["slot_scan"], "id": "h-scan", "interactive": True},
            ],
            "layout": {"type": "stack", "gap": "lg", "elements": [
                {"type": "header", "label": title},
                {"type": "text", "label": s["h1"], "size": "xl", "weight": "bold"},
                {"type": "text", "label": s["h1s"], "size": "md", "color": "secondary"},
            ]},
        },
        {
            "id": screen_ids[1], "kind": "kiosk-screen", "title": s["t2"],
            "stage_id": stage_ids[1], "state": "default",
            "layout": {"type": "stack", "gap": "md", "elements": [
                {"type": "header", "label": s["t2"]},
                {"type": "text", "label": s["h2"], "size": "lg", "weight": "bold"},
                {"type": "spacer", "size": "sm"},
                {"type": "grid", "cols": 3, "gap": "md", "elements": [
                    {"type": "card", "title": s["card_apple"]},
                    {"type": "card", "title": s["card_milk"]},
                    {"type": "card", "title": s["card_bread"]},
                ]},
                {"type": "spacer", "size": "md"},
                {"type": "button", "id": "checkout", "label": s["btn_done"], "variant": "primary", "interactive": True},
            ]},
        },
        {
            "id": screen_ids[2], "kind": "kiosk-screen", "title": s["t3"],
            "stage_id": stage_ids[2], "state": "success",
            "chrome": "panel",
            "hardware": [
                {"slot": "nfc", "position": "bottom", "label": s["slot_nfc"], "id": "h-nfc", "interactive": True},
            ],
            "layout": {"type": "stack", "gap": "lg", "elements": [
                {"type": "header", "label": s["t3"]},
                {"type": "text", "label": s["h3"], "size": "xl", "weight": "bold", "color": "success"},
            ]},
        },
    ]
    arrows = [
        {"from": f"{screen_ids[0]}#h-scan",    "to": screen_ids[1], "label": s["tx_scan"], "trigger": "tap", "kind": "default", "is_default": True},
        {"from": f"{screen_ids[1]}#checkout", "to": screen_ids[2], "label": s["tx_done"], "trigger": "tap", "kind": "default", "is_default": True},
        {"from": f"{screen_ids[2]}#h-nfc",    "to": screen_ids[0], "label": s["tx_pay"],  "trigger": "tap", "kind": "success"},
    ]
    return screens, arrows


def _seed_screens_desktop(*, language, title, screen_ids, stage_ids, step_labels) -> tuple[list[dict], list[dict]]:
    """Desktop seed: dashboard + detail + form (no chrome / side-keys)."""
    s = {
        "zh": {
            "t1": "概览", "t2": "详情", "t3": "新建",
            "h1": "欢迎回来", "h1s": "您有 3 项待办",
            "h2": "项目 A", "h2s": "状态:进行中", "btn_edit": "编辑",
            "h3": "新建项目", "btn_save": "保存",
            "form_name": "名称", "form_owner": "负责人",
            "tx_open": "查看项目", "tx_edit": "编辑", "tx_save": "保存",
            "card_a": "项目 A", "card_b": "项目 B", "card_c": "项目 C",
        },
        "en": {
            "t1": "Overview", "t2": "Detail", "t3": "Create",
            "h1": "Welcome back", "h1s": "You have 3 items pending",
            "h2": "Project A", "h2s": "Status: in progress", "btn_edit": "Edit",
            "h3": "New project", "btn_save": "Save",
            "form_name": "Name", "form_owner": "Owner",
            "tx_open": "Open project", "tx_edit": "Edit", "tx_save": "Save",
            "card_a": "Project A", "card_b": "Project B", "card_c": "Project C",
        },
    }[language]
    screens = [
        {
            "id": screen_ids[0], "kind": "desktop-window", "title": s["t1"],
            "stage_id": stage_ids[0], "state": "default",
            "layout": {"type": "stack", "gap": "lg", "elements": [
                {"type": "header", "label": title},
                {"type": "text", "label": s["h1"], "size": "xl", "weight": "bold"},
                {"type": "text", "label": s["h1s"], "size": "sm", "color": "secondary"},
                {"type": "spacer", "size": "md"},
                {"type": "grid", "cols": 3, "gap": "md", "elements": [
                    {"type": "card", "id": "card-a", "title": s["card_a"], "body": s["h2s"], "interactive": True},
                    {"type": "card", "title": s["card_b"], "body": s["h2s"]},
                    {"type": "card", "title": s["card_c"], "body": s["h2s"]},
                ]},
            ]},
        },
        {
            "id": screen_ids[1], "kind": "desktop-window", "title": s["t2"],
            "stage_id": stage_ids[1], "state": "default",
            "layout": {"type": "stack", "gap": "md", "elements": [
                {"type": "header", "label": s["t2"], "back": True},
                {"type": "text", "label": s["h2"], "size": "xl", "weight": "bold"},
                {"type": "text", "label": s["h2s"], "size": "md", "color": "secondary"},
                {"type": "spacer", "size": "md"},
                {"type": "button", "id": "edit", "label": s["btn_edit"], "variant": "primary", "interactive": True},
            ]},
        },
        {
            "id": screen_ids[2], "kind": "desktop-window", "title": s["t3"],
            "stage_id": stage_ids[2], "state": "warning",
            "layout": {"type": "stack", "gap": "md", "elements": [
                {"type": "header", "label": s["t3"]},
                {"type": "form-field", "id": "name", "label": s["form_name"], "placeholder": "..."},
                {"type": "form-field", "id": "owner", "label": s["form_owner"], "placeholder": "..."},
                {"type": "spacer", "size": "md"},
                {"type": "button", "id": "save", "label": s["btn_save"], "variant": "primary", "interactive": True},
            ]},
        },
    ]
    arrows = [
        {"from": f"{screen_ids[0]}#card-a", "to": screen_ids[1], "label": s["tx_open"], "trigger": "tap", "kind": "default", "is_default": True},
        {"from": f"{screen_ids[1]}#edit",   "to": screen_ids[2], "label": s["tx_edit"], "trigger": "tap", "kind": "default", "is_default": True},
        {"from": f"{screen_ids[2]}#save",   "to": screen_ids[0], "label": s["tx_save"], "trigger": "tap", "kind": "success"},
    ]
    return screens, arrows


def _seed_screens_tv(*, language, title, screen_ids, stage_ids, step_labels) -> tuple[list[dict], list[dict]]:
    """TV seed: horizontal carousel + detail + play. Loading state on play."""
    s = {
        "zh": {
            "t1": "首页", "t2": "节目详情", "t3": "正在播放",
            "h1": "猜你喜欢", "card_a": "节目 A", "card_b": "节目 B", "card_c": "节目 C", "card_d": "节目 D",
            "h2": "节目 A · 第 1 集", "btn_play": "播放",
            "h3": "00:23 / 45:00",
            "tx_open": "选中节目", "tx_play": "播放", "tx_done": "播放完毕",
        },
        "en": {
            "t1": "Home", "t2": "Show detail", "t3": "Now playing",
            "h1": "Recommended for you", "card_a": "Show A", "card_b": "Show B", "card_c": "Show C", "card_d": "Show D",
            "h2": "Show A · S1E1", "btn_play": "Play",
            "h3": "00:23 / 45:00",
            "tx_open": "Select", "tx_play": "Play", "tx_done": "End",
        },
    }[language]
    screens = [
        {
            "id": screen_ids[0], "kind": "tv-screen", "title": s["t1"],
            "stage_id": stage_ids[0], "state": "default",
            "layout": {"type": "stack", "gap": "lg", "elements": [
                {"type": "header", "label": title},
                {"type": "text", "label": s["h1"], "size": "xl", "weight": "bold"},
                {"type": "grid", "cols": 4, "gap": "md", "elements": [
                    {"type": "card", "id": "card-a", "title": s["card_a"], "interactive": True, "state": "hover"},
                    {"type": "card", "title": s["card_b"]},
                    {"type": "card", "title": s["card_c"]},
                    {"type": "card", "title": s["card_d"]},
                ]},
            ]},
        },
        {
            "id": screen_ids[1], "kind": "tv-screen", "title": s["t2"],
            "stage_id": stage_ids[1], "state": "default",
            "layout": {"type": "stack", "gap": "lg", "elements": [
                {"type": "image-placeholder", "ratio": "16:9", "label": "Cover art"},
                {"type": "text", "label": s["h2"], "size": "xl", "weight": "bold"},
                {"type": "button", "id": "play", "label": s["btn_play"], "variant": "primary", "interactive": True},
            ]},
        },
        {
            "id": screen_ids[2], "kind": "tv-screen", "title": s["t3"],
            "stage_id": stage_ids[2], "state": "loading",
            "layout": {"type": "stack", "gap": "lg", "elements": [
                {"type": "image-placeholder", "ratio": "16:9", "label": "Playing..."},
                {"type": "text", "label": s["h3"], "size": "md", "color": "secondary"},
                {"type": "progress", "kind": "linear", "value": 5},
            ]},
        },
    ]
    arrows = [
        {"from": f"{screen_ids[0]}#card-a", "to": screen_ids[1], "label": s["tx_open"], "trigger": "tap",  "kind": "default", "is_default": True},
        {"from": f"{screen_ids[1]}#play",   "to": screen_ids[2], "label": s["tx_play"], "trigger": "tap",  "kind": "default", "is_default": True},
        {"from": screen_ids[2],             "to": screen_ids[0], "label": s["tx_done"], "trigger": "auto", "kind": "default", "delay_ms": 0},
    ]
    return screens, arrows


def build_mermaid(journey: dict) -> str:
    """Render the stages as a mermaid flowchart body (indented for codeblock).

    Uses the shared escape_label_for_mermaid helper so any embedded
    newlines, parens, brackets, or double quotes in stage labels become
    renderer-safe (literal `\\n` and real newlines → `<br/>`).
    """
    stages = journey.get("stages", [])
    if not stages:
        return "    %% No stages yet"
    nodes = [
        f'    {s["id"]}[{escape_label_for_mermaid(s["label"])}]'
        for s in stages
    ]
    edges = [
        f"    {stages[i]['id']} --> {stages[i + 1]['id']}"
        for i in range(len(stages) - 1)
    ]
    return "\n".join(nodes + edges)


def render_template(
    template: str,
    *,
    title: str,
    subtitle: str,
    language: str,
    persona_name: str,
    persona_slug: str,
    persona_role: str,
    first_stage_label: str,
    mermaid_body: str,
    date: str,
    journey_json: str,
    design_tokens_json: str,
) -> str:
    """Substitute the {{TOKEN}} placeholders in a template string."""
    mapping = {
        "{{TITLE}}": title,
        "{{SUBTITLE}}": subtitle,
        "{{LANG}}": language,
        "{{PERSONA_NAME}}": persona_name,
        "{{PERSONA_SLUG}}": persona_slug,
        "{{PERSONA_ROLE}}": persona_role,
        "{{FIRST_STAGE_LABEL}}": first_stage_label,
        "{{MERMAID_BODY}}": mermaid_body,
        "{{DATE}}": date,
        "{{JOURNEY_JSON}}": journey_json,
        "{{DESIGN_TOKENS_JSON}}": design_tokens_json,
    }
    out = template
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out


def parse_design_frontmatter(md_text: str) -> dict:
    """Extract DESIGN.md YAML frontmatter into a python dict.

    Hand-rolled mini-parser — no PyYAML dependency. Supports the subset used
    by our design-style presets: top-level scalars + nested maps two levels
    deep with string/numeric scalar leaves.
    """
    if not md_text.startswith("---"):
        return {}
    parts = md_text.split("---", 2)
    if len(parts) < 3:
        return {}
    yaml_text = parts[1].strip("\n")
    return _parse_simple_yaml(yaml_text)


def _parse_simple_yaml(text: str) -> dict:
    """Very small YAML subset parser: top-level keys + 2 levels of nested maps."""
    root: dict = {}
    stack: list[tuple[int, dict]] = [(0, root)]
    for raw in text.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        while stack and indent < stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else root
        if value == "":
            child: dict = {}
            parent[key] = child
            stack.append((indent + 2, child))
        else:
            parent[key] = _coerce_scalar(value)
    return root


def _coerce_scalar(value: str):
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


# ---------------------------------------------------------------------------
# Filesystem ops
# ---------------------------------------------------------------------------

def copy_workspace_template(dst: Path, *, force: bool) -> None:
    """Copy the template tree (HTML, CSS, JS, README, preview.py) into dst."""
    dst.mkdir(parents=True, exist_ok=True)
    if not force and any(dst.iterdir()):
        raise FileExistsError(
            f"workspace {dst} is not empty. Pass --force to overwrite."
        )
    assets_src = WORKSPACE_TPL / "assets"
    (dst / "assets").mkdir(exist_ok=True)
    for path in assets_src.iterdir():
        if path.is_file():
            shutil.copy2(path, dst / "assets" / path.name)
    shutil.copy2(WORKSPACE_TPL / "preview.py", dst / "preview.py")
    (dst / "preview.py").chmod(0o755)


def write_outputs(
    workspace: Path,
    *,
    journey: dict,
    design_md_text: str,
    design_tokens: dict,
    journey_md_text: str,
    index_html_text: str,
    readme_text: str,
) -> None:
    (workspace / "DESIGN.md").write_text(design_md_text, encoding="utf-8")
    (workspace / "journey.json").write_text(
        json.dumps(journey, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (workspace / "JOURNEY.md").write_text(journey_md_text, encoding="utf-8")
    (workspace / "index.html").write_text(index_html_text, encoding="utf-8")
    (workspace / "README.md").write_text(readme_text, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI orchestration
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    workspace = Path(args.path).expanduser().resolve()
    language = args.language or "en"
    if language not in VALID_LANGUAGES:
        print(f"error: --language must be one of {sorted(VALID_LANGUAGES)}", file=sys.stderr)
        return 2
    try:
        design_path = resolve_design_style(args.design_style)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    title = args.title or workspace.name
    subtitle = args.subtitle or ""
    persona_name = args.persona or ("Primary user" if language == "en" else "主要用户")
    persona_role = args.persona_role or (
        "Primary user of the product" if language == "en" else "产品主要使用者"
    )

    device_kind = args.device_kind or "mobile"
    if device_kind not in VALID_DEVICE_KINDS:
        print(
            f"error: --device-kind must be one of {sorted(VALID_DEVICE_KINDS)}",
            file=sys.stderr,
        )
        return 2

    journey = build_initial_journey(
        title=title,
        subtitle=subtitle,
        persona_name=persona_name,
        persona_role=persona_role,
        language=language,
        device_kind=device_kind,
    )

    design_md_text = design_path.read_text(encoding="utf-8")
    design_tokens = parse_design_frontmatter(design_md_text)

    mermaid_body = build_mermaid(journey)
    first_stage_label = journey["stages"][0]["label"] if journey["stages"] else ""

    journey_json_inline = json.dumps(journey, indent=2, ensure_ascii=False)
    design_tokens_inline = json.dumps(design_tokens, indent=2, ensure_ascii=False)

    journey_md_tpl = (WORKSPACE_TPL / "JOURNEY.md").read_text(encoding="utf-8")
    index_html_tpl = (WORKSPACE_TPL / "index.html").read_text(encoding="utf-8")
    readme_tpl = (WORKSPACE_TPL / "README.md").read_text(encoding="utf-8")

    today = datetime.now().strftime("%Y-%m-%d")
    common_kwargs = dict(
        title=title,
        subtitle=subtitle,
        language=language,
        persona_name=persona_name,
        persona_slug=journey["personas"][0]["id"],
        persona_role=persona_role,
        first_stage_label=first_stage_label,
        mermaid_body=mermaid_body,
        date=today,
        journey_json=journey_json_inline,
        design_tokens_json=design_tokens_inline,
    )
    journey_md_text = render_template(journey_md_tpl, **common_kwargs)
    index_html_text = render_template(index_html_tpl, **common_kwargs)
    readme_text = render_template(readme_tpl, **common_kwargs)

    if args.dry_run:
        print(f"[dry-run] would create workspace at {workspace}")
        print(f"[dry-run] design style: {design_path.name}")
        print(f"[dry-run] language: {language}")
        print(f"[dry-run] stages: {len(journey['stages'])}")
        return 0

    try:
        copy_workspace_template(workspace, force=args.force)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_outputs(
        workspace,
        journey=journey,
        design_md_text=design_md_text,
        design_tokens=design_tokens,
        journey_md_text=journey_md_text,
        index_html_text=index_html_text,
        readme_text=readme_text,
    )

    print(f"OK: workspace created at {workspace}")
    print(f"  design style:  {design_path.stem}")
    print(f"  device kind:   {device_kind}")
    print(f"  language:      {language}")
    print(f"  stages:        {len(journey['stages'])} (skeleton)")
    print()
    print(f"  open:  double-click {workspace / 'index.html'}")
    print(f"  or:    cd {workspace} && python3 preview.py")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize a user-journey workspace.",
    )
    parser.add_argument(
        "--path",
        help="destination directory for the workspace (required unless --list-styles is set)",
    )
    parser.add_argument(
        "--title",
        help="title of the journey (defaults to the workspace directory name)",
    )
    parser.add_argument(
        "--subtitle",
        default="",
        help="one-line scope statement ('from X to Y')",
    )
    parser.add_argument(
        "--persona",
        help="primary persona name",
    )
    parser.add_argument(
        "--persona-role",
        help="primary persona role description",
    )
    parser.add_argument(
        "--language",
        choices=sorted(VALID_LANGUAGES),
        default="en",
        help="language for default labels and template prose",
    )
    parser.add_argument(
        "--design-style",
        default="corporate-clean",
        help="design-style preset slug (see SKILL_PATH/templates/design-styles/)",
    )
    parser.add_argument(
        "--device-kind",
        choices=sorted(VALID_DEVICE_KINDS),
        default="mobile",
        help=(
            "primary device form of the journey. Drives the seed screens in "
            "journey.json so the workspace opens straight into a representative "
            "Flow view (ATM gets chrome + side-key-rail, kiosk gets scanner + nfc, "
            "TV gets carousel, etc.). The AI is expected to continue with the "
            "same vocabulary in Pass C."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing files if the workspace is not empty",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would happen without writing any files",
    )
    parser.add_argument(
        "--list-styles",
        action="store_true",
        help="list available design-style presets and exit",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if args.list_styles:
        for name in list_design_styles():
            print(name)
        sys.exit(0)
    if not args.path:
        print("error: --path is required (or pass --list-styles to list presets)", file=sys.stderr)
        sys.exit(2)
    sys.exit(run(args))


if __name__ == "__main__":
    main()
