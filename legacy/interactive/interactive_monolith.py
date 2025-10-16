#!/usr/bin/env python3
# Minimal LMArena CLI with CSP-safe polling bridge + Prompt Studio + Book Modes + Lossless Transformer
# Features:
# - CSP-safe polling bridge (no WebSocket): /bridge/poll (browser polls), /bridge/push (chunks back)
# - ID capture via /internal/id_capture/update (Tampermonkey PerformanceObserver)
# - Prompt repository: zero2hero/reference/pop/exam-cram/lossless-rewrite/translate/brainstorm/style-transfer
# - Subject-aware book modes: /book.zero2hero <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]
#                           : /book.reference, /book.pop, /exam.cram (similar flags)
# - Lossless pipeline: /ingest.synth, /rewrite.lossless, /lossless.run
# - Style capture/apply: /style.capture, /style.apply
# - Study tools: /flashcards.from, /glossary.from, /index.from
# - Translate file: /translate.file <file> <language> [chunkKB=50]
# - Autopilot intervention: /next "<custom prompt>" one-shot override; /book.pause, /book.resume
# - Rolling history window: /window N
# - Colored UI, status, and sanity checks

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from typing import Dict, List

from aiohttp import web
from lma_stream import (
    anchor_from_text,
    build_anchor_continue_prompt,
    extract_text_chunks,
    jaccard_ngrams,
    strip_next_marker,
)
from lma_templates import (
    BOOK_PLAN_PROMPT,
    CHAD_TEMPLATE,
    NARRATIVE_OVERLAY,
    NO_BS_ADDENDUM,
    OUTPUT_BUDGET_ADDENDUM,
    PROMPT_REPO,
)

try:
    from openai import OpenAI as _OpenAIClient
except Exception:
    _OpenAIClient = None
try:
    import yaml
except ImportError:
    yaml = None
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings

    PTK_AVAILABLE = True
except ImportError:
    PTK_AVAILABLE = False

# Import new core components
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from src.lmastudio.core.pipeline import PipelineExecutor
except ImportError:
    PipelineExecutor = None


def load_json_auto(path):
    """Load JSON file, with transparent support for .gz compressed files."""
    import gzip
    import json
    import os

    if os.path.exists(path + ".gz"):
        with gzip.open(path + ".gz", "rt", encoding="utf-8") as f:
            return json.load(f)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------- Colors/UI ----------------
USE_COLOR = sys.stdout.isatty()


class C:
    R = ""
    B = ""
    DIM = ""
    OK = ""
    WARN = ""
    ERR = ""
    USER = ""
    ASSIST = ""
    INFO = ""


def _apply_colors():
    if not USE_COLOR:
        for k in list(C.__dict__.keys()):
            if k.isupper():
                setattr(C, k, "")
        return
    C.R = "\x1b[0m"
    C.B = "\x1b[1m"
    C.DIM = "\x1b[2m"
    C.OK = "\x1b[32m"
    C.WARN = "\x1b[33m"
    C.ERR = "\x1b[31m"
    C.USER = "\x1b[38;5;39m"
    C.ASSIST = "\x1b[38;5;190m"
    C.INFO = "\x1b[38;5;244m"


_apply_colors()


def hr(ch="-"):
    return ch * max(20, min(shutil.get_terminal_size((80, 20)).columns, 120))


def now():
    return datetime.now().strftime("%H:%M:%S")


def info(msg):
    print(f"{C.INFO}{msg}{C.R}")


def ok(msg):
    print(f"{C.OK}{msg}{C.R}")


def warn(msg):
    print(f"{C.WARN}{msg}{C.R}")


def err(msg):
    print(f"{C.ERR}{msg}{C.R}")


# ---------------- Basic utils ----------------
BOOKS_DIR = "books"


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "book"


def next_available_path(base_path: str) -> str:
    if not os.path.exists(base_path):
        return base_path
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root, ext = os.path.splitext(base_path)
    return f"{root}-{stamp}{ext or '.md'}"


# ---------------- Checkpoint/Macro Helpers ----------------
def _load_macros():
    global MACROS
    if os.path.exists(MACRO_FILE):
        try:
            with open(MACRO_FILE, "r", encoding="utf-8") as f:
                MACROS = json.load(f)
            ok(f"Loaded {len(MACROS)} macros.")
        except Exception as e:
            warn(f"Failed to load macros: {e}")
    else:
        MACROS = {}


def _save_macros():
    ensure_dir(os.path.dirname(MACRO_FILE))
    try:
        with open(MACRO_FILE, "w", encoding="utf-8") as f:
            json.dump(MACROS, f, indent=2)
        ok(f"Saved {len(MACROS)} macros to {MACRO_FILE}")
    except Exception as e:
        err(f"Failed to save macros: {e}")


def _run_macro(name: str, args: List[str]):
    if name not in MACROS:
        warn(f"Macro '{name}' not found.")
        return None

    template = MACROS[name]

    # Simple positional argument substitution: ${1}, ${2}, etc.
    # Also supports ${1|slug} for slugified argument
    def replace_arg(match):
        full_match = match.group(0)
        parts = match.group(1).split("|")
        index = int(parts[0])
        modifier = parts[1] if len(parts) > 1 else None

        if index > 0 and index <= len(args):
            value = args[index - 1]
            if modifier == "slug":
                return slugify(value)
            return value
        return full_match

    # Replace ${N} or ${N|slug}
    command = re.sub(r"\$\{(\d+)(\|slug)?\}", replace_arg, template)

    return command


async def book_save(name: str | None = None):
    global AUTO_OUT, AUTO_COUNT, LAST_NEXT_HINT, SYSTEM_PROMPT, HISTORY, AUTO_MAX

    if not AUTO_OUT:
        warn("Autopilot not running or AUTO_OUT is unset. Cannot save checkpoint.")
        return

    slug = slugify(name or os.path.basename(AUTO_OUT))
    ensure_dir(CHECKPOINT_DIR)

    checkpoint_data = {
        "timestamp": datetime.now().isoformat(),
        "auto_out": AUTO_OUT,
        "auto_count": AUTO_COUNT,
        "auto_max": AUTO_MAX,
        "last_next_hint": LAST_NEXT_HINT,
        "system_prompt": SYSTEM_PROMPT,
        "history": HISTORY,
        "cont_mode": CONT_MODE,
        "cont_anchor_chars": CONT_ANCHOR_CHARS,
        "output_min_chars": OUTPUT_MIN_CHARS,
        "output_push_max_passes": OUTPUT_PUSH_MAX_PASSES,
        "backend": BACKEND,
        "model_id": MODEL_ID,
    }

    path = os.path.join(CHECKPOINT_DIR, f"{slug}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)
        ok(f"Checkpoint saved: {path}")
    except Exception as e:
        err(f"Failed to save checkpoint: {e}")


async def book_load(name: str):
    global AUTO_OUT, AUTO_COUNT, LAST_NEXT_HINT, SYSTEM_PROMPT, HISTORY, AUTO_MAX
    global CONT_MODE, CONT_ANCHOR_CHARS, OUTPUT_MIN_CHARS, OUTPUT_PUSH_MAX_PASSES, BACKEND, MODEL_ID

    path = os.path.join(CHECKPOINT_DIR, f"{slugify(name)}.json")
    if not os.path.exists(path):
        warn(f"Checkpoint not found: {path}")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        AUTO_OUT = data.get("auto_out")
        AUTO_COUNT = data.get("auto_count", 0)
        AUTO_MAX = data.get("auto_max")
        LAST_NEXT_HINT = data.get("last_next_hint")
        SYSTEM_PROMPT = data.get("system_prompt", "")
        HISTORY = data.get("history", [])
        CONT_MODE = data.get("cont_mode", CONT_MODE)
        CONT_ANCHOR_CHARS = data.get("cont_anchor_chars", CONT_ANCHOR_CHARS)
        OUTPUT_MIN_CHARS = data.get("output_min_chars", OUTPUT_MIN_CHARS)
        OUTPUT_PUSH_MAX_PASSES = data.get(
            "output_push_max_passes", OUTPUT_PUSH_MAX_PASSES
        )
        BACKEND = data.get("backend", BACKEND)
        MODEL_ID = data.get("model_id", MODEL_ID)

        ok(f"Checkpoint loaded: {path}")
        show_status()

        # Offer to resume
        global AUTO_ON, AUTO_TASK
        if AUTO_OUT and not AUTO_ON:
            warn(
                "Autopilot is currently OFF. Use /book.start or /book.resume to continue."
            )

    except Exception as e:
        err(f"Failed to load checkpoint: {e}")


# ---------------- Bridge state ----------------
PENDING_JOBS = []  # [{request_id, payload}]
RESPONSE_CHANNELS = {}  # req_id -> asyncio.Queue
CAPTURE_FLAG = False
CLIENT_SEEN = False

# ---------------- Chat state ----------------
SESSION_ID = ""
MESSAGE_ID = ""
MODEL_ID = None
SYSTEM_PROMPT = ""
HISTORY = []  # [{"role":"user"/"assistant","content":...}]
HISTORY_WINDOW = 80  # last N exchanges (user+assistant=2)

# ---------------- No-Bullshit additions ----------------
NO_BS_ACTIVE = False

# ---- Prompt Booster templates ----
PROMPT_BOOST_TEMPLATE = """You are a prompt engineer optimizing for this system’s behavior.
Goal: deliver the best single prompt for the user’s objective.

If critical details are missing, ask up to 5 concise questions first. Otherwise skip questions.
When ready, output only:

PROMPT: <final improved prompt, ready to send to the model>
RATIONALE: <1–5 lines on why it’s better>

If you need to ask questions first, output only:

QUESTIONS:
- Q1 ...
- Q2 ...
- (<=5)
"""

META_PROMPT_BOOST_TEMPLATE = """You advise the Prompt Booster. Given the user goal and our tool’s capabilities, propose the best scaffold for the Booster prompt (framing, constraints, guardrails).

Output only:
BOOSTER_SCAFFOLD: <instructions the Booster should use>
WHEN_TO_USE: <short conditions when this scaffold helps>
"""

# ---------------- Autopilot ----------------
AUTO_ON = False
AUTO_TASK = None
AUTO_OUT = None
AUTO_COUNT = 0
AUTO_MAX = None
AUTO_DELAY = 1.0
LAST_NEXT_HINT = None
SAVE_SYSTEM_STACK: list[str] = []  # push/pop system alters
NEXT_OVERRIDE: str | None = None  # one-shot override for the next prompt
AUTO_PAUSE = False  # pause autopilot after finishing a chunk

# ---- Prompt Booster state ----
BOOST_PENDING: dict | None = None  # {"goal": str, "questions": list[str]}
BOOST_LAST_PROMPT: str | None = None
CANCEL_REQUESTED: bool = False  # console cancel flag

# ---- Project/Checkpoint/Macro state ----
PROJECT_ROOT = os.getcwd()
PROJECT_CONFIG: dict = {}
CHECKPOINT_DIR = os.path.join(PROJECT_ROOT, ".lmastudio", "checkpoints")
MACRO_FILE = os.path.join(PROJECT_ROOT, ".lmastudio", "macros.json")
MACROS: Dict[str, str] = {}

# --- Self-study continuation hammer ---
SESSION_MODE = None  # e.g., "zero2hero", None otherwise
COVERAGE_HAMMER_ON = (
    True  # when True, add a minimal anti-wrap-up line to continue prompts
)
NARRATIVE_ACTIVE = False  # narrative/pedagogy overlay ON/OFF

# --- Output budget / push-to-max controls ---
OUTPUT_BUDGET_SNIPPET_ON = True  # append system prompt addendum on book modes
OUTPUT_PUSH_ON = True  # auto-extend within the same subtopic to hit a min length
OUTPUT_MIN_CHARS = 4500  # target minimal chunk size before moving on (tune as needed)
OUTPUT_PUSH_MAX_PASSES = (
    3  # at most N extra "continue within current subtopic" micro-steps
)

# --- Cloudflare controls ---
CF_BLOCKED = False  # true while CF challenge is active
CF_NOTIFIED = False  # ensure we print the notice only once per CF event

# --- Backend switch ---
BACKEND = "bridge"  # bridge | openrouter

# --- OpenRouter config/state ---
OR_CLIENT = None
OR_MODEL = os.getenv(
    "OPENROUTER_MODEL"
)  # e.g., "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
OR_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OR_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
OR_REFERRER = os.getenv("OPENROUTER_REFERRER")  # optional
OR_TITLE = os.getenv("OPENROUTER_TITLE")  # optional
OR_HEADERS = None  # built in init

# --- Continuation controls ---
CONT_MODE = "anchor"  # "anchor" (default) or "normal"
CONT_ANCHOR_CHARS = (
    200  # how many chars from the end of last assistant chunk to use as anchor
)
REPEAT_WARN = True  # warn and auto-pause if high repetition detected
REPEAT_NGRAM = 4  # n-gram size for repetition scoring
REPEAT_THRESH = 0.35  # Jaccard threshold to warn (0..1); lower = more sensitive
IMAGE_MARKDOWN = True  # when True, convert a2 image chunks to markdown

# ---------------- Ingestion/Synthesis ----------------
ING_ON = False
ING_TASK = None
ING_MODE = None  # "ack", "synth", "style"
ING_PATH = None
ING_POS = 0
ING_TOTAL = 0
ING_CHUNK_BYTES = 0
SYNTH_TEXT = ""
SYNTH_LIMIT = 9500
SYNTH_OUT = None

# ---------------- Parsers ----------------


def any_end_marker(text: str) -> bool:
    if not text:
        return False
    for m in NEXT_RE.finditer(text):
        val = (m.group(1) or "").strip().upper()
        if val in {"END", "DONE", "STOP", "FINISHED"}:
            return True
    return False


def last_assistant_text() -> str:
    for m in reversed(HISTORY):
        if m["role"] == "assistant":
            return m.get("content") or ""
    return ""


ERROR_RE = re.compile(r'(\{\s*"error".*?\})', re.DOTALL)
FINISH_RE = re.compile(r'[ab]d:(\{.*?"finishReason".*?\})', re.DOTALL)
CF_PATTERNS = [
    r"<title>Just a moment...</title>",
    r"Enable JavaScript and cookies to continue",
]
NEXT_RE = re.compile(r"^\s*NEXT:\s*(.+)\s*$", re.MULTILINE)
IMAGE_RE = re.compile(r"[ab]2:(\[.*?\])")


def continuation_anchor(tail_chars: int) -> str:
    prev = last_assistant_text()
    if not prev:
        return ""
    s = prev[-tail_chars:]
    # trim to sentence boundary if possible
    p = max(s.rfind("."), s.rfind("!"), s.rfind("?"))
    if p != -1 and p >= len(s) - 120:  # try to end on sentence end near the tail
        s = s[: p + 1]
    return s.strip()


# ---------------- HTTP helpers ----------------
def _add_cors(resp: web.StreamResponse):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Private-Network"] = "true"
    return resp


# ---------------- Bridge endpoints (poll/push) ----------------
async def bridge_poll(request: web.Request):
    global CAPTURE_FLAG, CLIENT_SEEN
    first = not CLIENT_SEEN
    CLIENT_SEEN = True
    resp = {"hello": True, "capture": CAPTURE_FLAG, "job": None}
    if CAPTURE_FLAG:
        CAPTURE_FLAG = False
    if PENDING_JOBS:
        resp["job"] = PENDING_JOBS.pop(0)
    if first:
        print()
        ok(f"[{now()}] Browser polling active.")
        print("> ", end="", flush=True)
    return _add_cors(web.json_response(resp))


async def bridge_push(request: web.Request):
    try:
        data = await request.json()
        req_id = data.get("request_id")
        payload = data.get("data")
        if not req_id:
            return _add_cors(
                web.json_response({"error": "missing request_id"}, status=400)
            )
        q = RESPONSE_CHANNELS.get(req_id)
        if q:
            await q.put(payload)
        return _add_cors(web.json_response({"status": "ok"}))
    except Exception as e:
        return _add_cors(web.json_response({"error": str(e)}, status=500))


# ---------------- ID capture ----------------
async def id_capture_update(request: web.Request):
    global SESSION_ID, MESSAGE_ID
    if request.method == "OPTIONS":
        return _add_cors(web.Response(text=""))
    try:
        data = await request.json()
        sid, mid = data.get("sessionId"), data.get("messageId")
        if not (sid and mid):
            return _add_cors(
                web.json_response(
                    {"error": "missing sessionId or messageId"}, status=400
                )
            )
        SESSION_ID, MESSAGE_ID = sid, mid
        print()
        ok(f"[{now()}] IDs updated:")
        print(f"    session_id = {SESSION_ID}\n    message_id = {MESSAGE_ID}")
        print("> ", end="", flush=True)
        return _add_cors(web.json_response({"status": "ok"}))
    except Exception as e:
        return _add_cors(web.json_response({"error": str(e)}, status=500))


# ---------------- Health ----------------
async def healthz(_req):
    return web.json_response({"status": "ok"})


# ---------------- Chat payload helpers ----------------
def trimmed_history():
    if HISTORY_WINDOW <= 0:
        return []
    n = HISTORY_WINDOW * 2
    return HISTORY[-n:] if len(HISTORY) > n else HISTORY


def build_payload(user_text: str) -> dict:
    templates = []
    if SYSTEM_PROMPT.strip():
        templates.append(
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
                "attachments": [],
                "participantPosition": "b",
            }
        )
    for m in trimmed_history():
        templates.append(
            {
                "role": m["role"],
                "content": m["content"],
                "attachments": [],
                "participantPosition": "a",
            }
        )
    templates.append(
        {
            "role": "user",
            "content": user_text,
            "attachments": [],
            "participantPosition": "a",
        }
    )
    return {
        "message_templates": templates,
        "target_model_id": MODEL_ID,
        "session_id": SESSION_ID,
        "message_id": MESSAGE_ID,
        "is_image_request": False,
    }


def build_payload_custom(messages: list[dict]) -> dict:
    templates = []
    for m in messages:
        pos = "b" if m["role"] == "system" else "a"
        templates.append(
            {
                "role": m["role"],
                "content": m["content"],
                "attachments": [],
                "participantPosition": pos,
            }
        )
    return {
        "message_templates": templates,
        "target_model_id": MODEL_ID,
        "session_id": SESSION_ID,
        "message_id": MESSAGE_ID,
        "is_image_request": False,
    }


async def send_and_collect(payload: dict, silent: bool = False) -> str:
    global CF_BLOCKED, CF_NOTIFIED, CANCEL_REQUESTED
    # Backend switch
    if BACKEND == "openrouter":
        return await _send_and_collect_openrouter(payload, silent=silent)
    if not CLIENT_SEEN:
        warn(
            "No browser polling detected. Open https://lmarena.ai with the userscript enabled."
        )
        return ""
    if not SESSION_ID or not MESSAGE_ID:
        warn(
            "Missing session/message IDs. Use /capture then click Retry in LMArena, or /setids."
        )
        return ""

    req_id = str(uuid.uuid4())
    q: asyncio.Queue = asyncio.Queue()
    RESPONSE_CHANNELS[req_id] = q
    PENDING_JOBS.append({"request_id": req_id, "payload": payload})

    buf = ""
    parts = []
    if not silent:
        print(f"{C.ASSIST}{C.B}Assistant{C.R}: ", end="", flush=True)
    try:
        while True:
            if CANCEL_REQUESTED:
                if not silent:
                    print(f"\n{C.WARN}[cancelled by user]{C.R}")
                RESPONSE_CHANNELS.pop(req_id, None)
                return "".join(parts)
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            if isinstance(chunk, dict) and "error" in chunk:
                msg = str(chunk["error"])
                if "401" in msg or "m2m" in msg.lower() or "auth" in msg.lower():
                    if not silent:
                        print(
                            f"\n{C.WARN}! Auth not captured. Click Retry once in LMArena, then try again.{C.R}"
                        )
                else:
                    if not silent:
                        print(f"\n{C.ERR}! Error: {msg}{C.R}")
                break
            if chunk == "[DONE]":
                break
            buf += str(chunk)

            for p in CF_PATTERNS:
                if re.search(p, buf, re.IGNORECASE):
                    # Set CF flags once; avoid repeated prints
                    CF_BLOCKED = True
                    if not CF_NOTIFIED and not silent:
                        print(f"\n{C.WARN}Cloudflare detected. Pausing nicely.{C.R}")
                        print(
                            f"{C.INFO}Please switch to the browser, complete the challenge, then run /cf.resume (and /book.resume if paused).{C.R}"
                        )
                        CF_NOTIFIED = True
                    RESPONSE_CHANNELS.pop(req_id, None)
                    return "".join(parts)

            m = ERROR_RE.search(buf)
            if m:
                try:
                    errj = json.loads(m.group(1))
                    if not silent:
                        print(f"\n{C.ERR}! LMArena error: {errj.get('error')}{C.R}")
                    RESPONSE_CHANNELS.pop(req_id, None)
                    return "".join(parts)
                except Exception:
                    pass

            texts, buf = extract_text_chunks(buf)
            for t in texts:
                parts.append(t)
                if not silent:
                    print(t, end="", flush=True)

            # Handle inline image chunks → Markdown
            if IMAGE_MARKDOWN:
                im = IMAGE_RE.search(buf)
                while im:
                    try:
                        image_data_list = json.loads(im.group(1))
                        if isinstance(image_data_list, list) and image_data_list:
                            image_info = image_data_list[0]
                            if (
                                image_info.get("type") == "image"
                                and "image" in image_info
                            ):
                                md = f"![Image]({image_info['image']})"
                                parts.append(md)
                                if not silent:
                                    print(md, end="", flush=True)
                    except Exception:
                        pass
                    buf = buf[im.end() :]
                    im = IMAGE_RE.search(buf)

            mf = FINISH_RE.search(buf)
            if mf:
                buf = buf[mf.end() :]
    except asyncio.TimeoutError:
        if not silent:
            print(f"\n{C.WARN}! Timed out waiting for response.{C.R}")

    if not silent:
        print()
    if CANCEL_REQUESTED and not silent:
        print(f"{C.INFO}(note: cancel flag cleared){C.R}")
    CANCEL_REQUESTED = False
    RESPONSE_CHANNELS.pop(req_id, None)
    return "".join(parts)


# ---------------- Public chat helpers ----------------
async def ask_collect(user_text: str):
    print()
    print(f"{C.USER}{C.B}You{C.R}: {user_text}\n")
    reply = await send_and_collect(build_payload(user_text))
    print(hr())
    HISTORY.append({"role": "user", "content": user_text})
    HISTORY.append({"role": "assistant", "content": reply})
    return reply


def write_to_file(path: str, text: str):
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "a", encoding="utf-8") as f:
        f.write(text + "\n\n")


def _or_init(force: bool = False):
    global OR_CLIENT, OR_HEADERS
    if OR_CLIENT and not force:
        return
    if _OpenAIClient is None:
        raise RuntimeError(
            "openai package not installed. Run: pip install 'openai>=1.20.0'"
        )
    if not OR_API_KEY:
        raise RuntimeError(
            "Missing API key. Set OPENROUTER_API_KEY or OPENAI_API_KEY in your environment."
        )
    OR_CLIENT = _OpenAIClient(base_url=OR_BASE_URL, api_key=OR_API_KEY)
    headers = {}
    if OR_REFERRER:
        headers["HTTP-Referer"] = OR_REFERRER
    if OR_TITLE:
        headers["X-Title"] = OR_TITLE
    OR_HEADERS = headers or None


def _or_convert_templates_to_messages(payload: dict) -> list:
    # payload is the same dict we send to the bridge; we just map to OpenAI format.
    messages = []
    tmpl = payload.get("message_templates") or []
    for m in tmpl:
        role = m.get("role") or "user"
        content = m.get("content") or ""
        messages.append({"role": role, "content": content})
    return messages


async def _send_and_collect_openrouter(payload: dict, silent: bool = False) -> str:
    # Convert templates -> OpenAI messages and stream
    _or_init()
    model = OR_MODEL or "openrouter/auto"
    messages = _or_convert_templates_to_messages(payload)

    # Stream via OpenAI client
    try:
        stream = OR_CLIENT.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            extra_headers=OR_HEADERS,
        )
    except Exception as e:
        if not silent:
            print(f"\n{C.ERR}! OpenRouter request failed: {e}{C.R}")
        return ""

    out_parts = []
    try:
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content or ""
            except Exception:
                delta = ""
            if delta:
                out_parts.append(delta)
                if not silent:
                    print(delta, end="", flush=True)
    except Exception as e:
        if not silent:
            print(f"\n{C.WARN}! Stream ended with error: {e}{C.R}")

    if not silent:
        print()
    return "".join(out_parts)


# ---------------- Autopilot core (intervention-ready) ----------------
async def autorun_loop():
    global AUTO_ON, AUTO_COUNT, LAST_NEXT_HINT, SYSTEM_PROMPT, NEXT_OVERRIDE, AUTO_PAUSE
    global HISTORY, AUTO_OUT, AUTO_MAX, AUTO_DELAY, CONT_MODE, CONT_ANCHOR_CHARS
    global REPEAT_WARN, REPEAT_THRESH, REPEAT_NGRAM, SESSION_MODE, COVERAGE_HAMMER_ON
    global OUTPUT_PUSH_ON, OUTPUT_MIN_CHARS, OUTPUT_PUSH_MAX_PASSES

    first = True
    while AUTO_ON and (AUTO_MAX is None or AUTO_COUNT < AUTO_MAX):
        # Pause support
        while AUTO_ON and AUTO_PAUSE:
            await asyncio.sleep(0.2)
        if not AUTO_ON:
            break

        # Decide next prompt
        if first:
            user_text = "BEGIN"
            first = False
        else:
            if NEXT_OVERRIDE:
                user_text = NEXT_OVERRIDE
                NEXT_OVERRIDE = None
            elif CONT_MODE == "anchor":
                anch = continuation_anchor(CONT_ANCHOR_CHARS)
                if anch:
                    user_text = build_anchor_continue_prompt(anch)
                    if SESSION_MODE == "zero2hero" and COVERAGE_HAMMER_ON:
                        user_text += "\nDo not conclude or summarize; coverage is not complete. Continue teaching the field and its subfields to the target depth."
                else:
                    user_text = "continue."
            else:
                user_text = "continue."

        print()
        print(f"{C.USER}{C.B}You{C.R}: {user_text}\n")

        # First segment
        reply = await send_and_collect(build_payload(user_text))
        body, hint = strip_next_marker(reply)  # strip NEXT from main body; capture hint
        LAST_NEXT_HINT = hint

        # Auto-extend within the same subtopic to hit OUTPUT_MIN_CHARS
        accumulated = body
        local_hint = hint
        micro = 0
        while (
            OUTPUT_PUSH_ON
            and len(accumulated) < OUTPUT_MIN_CHARS
            and micro < OUTPUT_PUSH_MAX_PASSES
            and AUTO_ON
        ):
            # Build a local anchor from the accumulated text (not from full HISTORY)
            local_anch = anchor_from_text(accumulated, CONT_ANCHOR_CHARS)
            ext_prompt = (
                build_anchor_continue_prompt(local_anch)
                + "\nFill to the per-response output limit within this same subtopic. "
                "Do not reintroduce or restart; continue exactly. "
                "Do not write a NEXT line yet; do not conclude."
            )
            print()
            print(f"{C.USER}{C.B}You{C.R}: [extend] {ext_prompt}\n")
            ext_reply = await send_and_collect(build_payload(ext_prompt))
            ext_body, ext_hint = strip_next_marker(
                ext_reply
            )  # strip any premature NEXT
            if not ext_body.strip():
                break
            # Optional repetition guard: stop if highly repetitive vs last portion
            if REPEAT_WARN:
                prev_tail = anchor_from_text(
                    accumulated, min(800, CONT_ANCHOR_CHARS * 4)
                )
                rep = jaccard_ngrams(
                    prev_tail, ext_body[: max(400, CONT_ANCHOR_CHARS)], n=REPEAT_NGRAM
                )
                if rep > REPEAT_THRESH:
                    warn(
                        f"High repetition during extension (Jaccard~{rep:.2f}). Stopping extend; you may /next steer."
                    )
                    break
            accumulated += ("\n\n" if not accumulated.endswith("\n") else "") + ext_body
            if ext_hint:  # keep only the last NEXT if the final step later adds it
                local_hint = ext_hint
            micro += 1

        # Now use the accumulated text as the final body for this iteration
        final_body = accumulated
        final_hint = local_hint

        # Persist to history and file
        HISTORY.append({"role": "user", "content": user_text})
        HISTORY.append({"role": "assistant", "content": final_body})
        if AUTO_OUT:
            write_to_file(AUTO_OUT, final_body)

        # Optional repetition detection (vs previous chunk)
        if REPEAT_WARN:
            prev_tail = continuation_anchor(min(800, CONT_ANCHOR_CHARS * 4))
            rep = jaccard_ngrams(
                prev_tail, final_body[: max(400, CONT_ANCHOR_CHARS)], n=REPEAT_NGRAM
            )
            if rep > REPEAT_THRESH:
                warn(
                    f"High repetition detected (Jaccard~{rep:.2f}). Auto-pausing. Use /next to steer or /book.resume."
                )
                AUTO_PAUSE = True

        AUTO_COUNT += 1

        # Auto-save checkpoint
        if AUTO_COUNT % 5 == 0 or not AUTO_ON:
            await book_save(os.path.basename(AUTO_OUT).replace(".md", ""))

        # Stop on explicit END
        if (
            any_end_marker(reply)
            or any_end_marker(final_body)
            or (
                final_hint and final_hint.upper() in {"END", "DONE", "STOP", "FINISHED"}
            )
        ):
            ok("NEXT: [END] detected — stopping.")
            AUTO_ON = False
            break

        # Carry hint forward (we do not inject hint text into the next prompt, we rely on anchors)
        LAST_NEXT_HINT = final_hint

        await asyncio.sleep(AUTO_DELAY)

    ok(
        f"Autopilot finished after {AUTO_COUNT} chunk(s). Output: {AUTO_OUT or '(none)'}"
    )
    if SAVE_SYSTEM_STACK:
        sys_old = SAVE_SYSTEM_STACK.pop()
        set_system(sys_old)


# ---------------- Chunking helpers ----------------
def chunks_by_bytes(text: str, max_bytes: int):
    b = text.encode("utf-8")
    out = []
    i = 0
    n = len(b)
    while i < n:
        j = min(i + max_bytes, n)
        if j < n:
            k = b.rfind(b"\n", i, j)
            if k == -1:
                k = b.rfind(b" ", i, j)
            if k != -1 and (j - k) < 2048:
                j = k
        part = b[i:j]
        while True:
            try:
                s = part.decode("utf-8")
                break
            except UnicodeDecodeError:
                part = part[:-1]
        out.append(s)
        i = j
    return out


# ---------------- Ingestion (ACK/SYNTH/STYLE) ----------------
INGEST_SYSTEM_ACK = (
    "You are in ingestion ACK mode. You will receive CHUNK i/N.\n"
    "Reply with exactly: OK i/N. Do not echo content. Do not add any other text."
)


def ingest_user_ack(i, n, chunk):
    return f"INGEST CHUNK {i}/{n}\n<BEGIN_CHUNK>\n{chunk}\n<END_CHUNK>\nReply with exactly: OK {i}/{n}\n"


INGEST_SYSTEM_SYNTH = (
    "You are a synthesis engine. You will receive the previous Synthesis and a new CHUNK.\n"
    "Update the Synthesis to incorporate the new material. Keep it compact but complete:\n"
    "structured outline of topics, key claims, procedures, defaults, signature heuristics, and stylistic guidance.\n"
    "Preserve earlier coverage; merge or refactor as needed.\n"
    "Return ONLY the updated Synthesis (Markdown), no commentary, no code fences."
)


def ingest_user_synth(i, n, synth_text, chunk, limit_chars):
    synth_excerpt = (
        synth_text[-limit_chars:] if len(synth_text) > limit_chars else synth_text
    )
    return (
        f"INGEST CHUNK {i}/{n}\n\n"
        f"PREVIOUS SYNTHESIS (<= {limit_chars} chars):\n<<<SYNTHESIS\n{synth_excerpt}\nSYNTHESIS>>>\n\n"
        f"NEW CHUNK:\n<<<CHUNK\n{chunk}\nCHUNK>>>\n\n"
        f"TASK:\n"
        f"- Update the Synthesis above to fully include the NEW CHUNK's information.\n"
        f"- Keep the updated Synthesis within ~{limit_chars} characters (short, dense).\n"
        f"- Return ONLY the updated Synthesis (Markdown), no commentary.\n"
    )


INGEST_SYSTEM_STYLE = (
    "You are a style profiler. Given an existing STYLE PROFILE and a new CHUNK, update the profile.\n"
    "Capture: tone, rhythm, sentence length, vocabulary, structure, devices, typical openings/closings, formatting, and no-goes.\n"
    "Return ONLY the updated STYLE PROFILE (Markdown), no commentary, no code fences."
)


def style_user_profile(i, n, style_text, chunk, limit_chars):
    excerpt = style_text[-limit_chars:] if len(style_text) > limit_chars else style_text
    return (
        f"STYLE CAPTURE CHUNK {i}/{n}\n\n"
        f"CURRENT STYLE PROFILE (<= {limit_chars} chars):\n<<<STYLE\n{excerpt}\nSTYLE>>>\n\n"
        f"NEW CHUNK:\n<<<CHUNK\n{chunk}\nCHUNK>>>\n\n"
        f"TASK:\n- Update the STYLE PROFILE to capture the author voice precisely.\n"
        f"- Keep within ~{limit_chars} characters.\n- Return ONLY the STYLE PROFILE."
    )


async def ingest_ack_loop(path: str, chunk_kb: int):
    global ING_ON, ING_MODE, ING_PATH, ING_POS, ING_TOTAL, ING_CHUNK_BYTES
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    ING_CHUNK_BYTES = max(8_000, int(chunk_kb * 1024))
    parts = chunks_by_bytes(text, ING_CHUNK_BYTES)
    ING_ON = True
    ING_MODE = "ack"
    ING_PATH = path
    ING_POS = 0
    ING_TOTAL = len(parts)
    ok(f"Ingest ACK mode: {ING_TOTAL} chunks (~{chunk_kb} KB each)")
    save_sys = SYSTEM_PROMPT
    save_win = HISTORY_WINDOW
    try:
        set_system(INGEST_SYSTEM_ACK)
        set_window(0)
        for idx, chunk in enumerate(parts, start=1):
            if not ING_ON:
                break
            msg = ingest_user_ack(idx, len(parts), chunk)
            reply = await send_and_collect(build_payload(msg), silent=True)
            print(f"[{now()}] Chunk {idx}/{len(parts)} ack: {reply.strip()[:50]}")
            ING_POS = idx
    finally:
        set_system(save_sys)
        set_window(save_win)
        ING_ON = False
        ING_MODE = None


async def ingest_synth_loop(path: str, synth_out: str, chunk_kb: int, synth_chars: int):
    global ING_ON, ING_MODE, ING_PATH, ING_POS, ING_TOTAL, ING_CHUNK_BYTES, SYNTH_LIMIT, SYNTH_TEXT, SYNTH_OUT
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    SYNTH_OUT = synth_out
    SYNTH_LIMIT = max(3000, int(synth_chars))
    ING_CHUNK_BYTES = max(10_000, int(chunk_kb * 1024))
    parts = chunks_by_bytes(text, ING_CHUNK_BYTES)
    ING_ON = True
    ING_MODE = "synth"
    ING_PATH = path
    ING_POS = 0
    ING_TOTAL = len(parts)
    ok(
        f"Ingest SYNTH mode: {ING_TOTAL} chunks (~{chunk_kb} KB each); synth limit ~{SYNTH_LIMIT} chars"
    )
    SYNTH_TEXT = ""
    save_sys = SYSTEM_PROMPT
    save_win = HISTORY_WINDOW
    try:
        set_system(INGEST_SYSTEM_SYNTH)
        set_window(0)
        for idx, chunk in enumerate(parts, start=1):
            if not ING_ON:
                break
            msg = ingest_user_synth(idx, len(parts), SYNTH_TEXT, chunk, SYNTH_LIMIT)
            reply = await send_and_collect(build_payload(msg), silent=True)
            SYNTH_TEXT = reply.strip()
            with open(SYNTH_OUT, "w", encoding="utf-8") as f:
                f.write(SYNTH_TEXT)
            print(
                f"[{now()}] Synth updated {idx}/{len(parts)} — {len(SYNTH_TEXT)} chars"
            )
            ING_POS = idx
    finally:
        set_system(save_sys)
        set_window(save_win)
        ING_ON = False
        ING_MODE = None
        ok(f"Synthesis saved to: {SYNTH_OUT}")


async def ingest_style_loop(path: str, out_path: str, chunk_kb: int, style_chars: int):
    global ING_ON, ING_MODE, ING_PATH, ING_POS, ING_TOTAL, ING_CHUNK_BYTES
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    ING_CHUNK_BYTES = max(10_000, int(chunk_kb * 1024))
    parts = chunks_by_bytes(text, ING_CHUNK_BYTES)
    style_profile = ""
    save_sys = SYSTEM_PROMPT
    save_win = HISTORY_WINDOW
    try:
        set_system(INGEST_SYSTEM_STYLE)
        set_window(0)
        ING_ON = True
        ING_MODE = "style"
        ING_PATH = path
        ING_POS = 0
        ING_TOTAL = len(parts)
        for idx, chunk in enumerate(parts, start=1):
            if not ING_ON:
                break
            msg = style_user_profile(idx, len(parts), style_profile, chunk, style_chars)
            reply = await send_and_collect(build_payload(msg), silent=True)
            style_profile = reply.strip()
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(style_profile)
            print(
                f"[{now()}] Style updated {idx}/{len(parts)} — {len(style_profile)} chars"
            )
            ING_POS = idx
    finally:
        set_system(save_sys)
        set_window(save_win)
        ING_ON = False
        ING_MODE = None
        ok(f"Style profile saved to: {out_path}")


# ---------------- Rewrite from synthesis ----------------
async def rewrite_start(
    synth_path: str, out_path: str, system_template: str | None = None
):
    with open(synth_path, "r", encoding="utf-8") as f:
        synth = f.read()
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    base_system = SYSTEM_PROMPT
    if system_template:
        base_system = system_template
        # Apply output budget addendum if this is a book lossless rewrite template
        if (
            "book.lossless.rewrite" in str(locals().get("system_template", ""))
            or len(synth) > 5000
        ):  # heuristic for lossless rewriting
            if OUTPUT_BUDGET_SNIPPET_ON:
                base_system = base_system.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(
        base_system
        + "\n\nSOURCE SYNTHESIS (for this session only):\n<<<SYNTHESIS\n"
        + synth
        + "\nSYNTHESIS>>>\n"
    )
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT
    AUTO_OUT = out_path
    AUTO_ON = True
    AUTO_COUNT = 0
    LAST_NEXT_HINT = None
    ok(f"Rewrite autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done():
        AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())


# ---------------- New: Chunked generation with system ----------------
async def chunked_generate_with_system(
    synth_path: str, system_template: str, out_path: str, max_chunks=None
):
    with open(synth_path, "r", encoding="utf-8") as f:
        synth = f.read()
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    base_system = system_template
    set_system(
        base_system
        + "\n\nSOURCE SYNTHESIS (for this session only):\n<<<SYNTHESIS\n"
        + synth
        + "\nSYNTHESIS>>>\n"
    )
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path
    AUTO_ON = True
    AUTO_COUNT = 0
    LAST_NEXT_HINT = None
    AUTO_MAX = max_chunks
    ok(f"Chunked generation autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done():
        AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())


def repo_list():
    rows = []
    for k, v in PROMPT_REPO.items():
        rows.append(f"- {k}: {v['title']} — {v['desc']}")
    return "\n".join(rows)


def repo_render(key: str, **kw) -> str:
    tpl = PROMPT_REPO[key]["system"]
    out = tpl
    # {subject}/{lang}
    for k2, v in kw.items():
        out = out.replace("{" + k2 + "}", v)
    # [FIELD] -> subject string
    if "subject" in kw:
        out = out.replace("[FIELD]", kw["subject"])
    return out


# ---------------- Prompt Booster Helpers ----------------
PROMPT_SECTION_RE = re.compile(
    r"^\s*(PROMPT|RATIONALE|QUESTIONS|BOOSTER_SCAFFOLD|WHEN_TO_USE)\s*:\s*",
    re.IGNORECASE | re.MULTILINE,
)


def _split_booster_sections(text: str) -> dict:
    # Simple splitter for PROMPT / RATIONALE / QUESTIONS (and meta sections)
    out = {}
    # Tag positions
    tags = []
    for m in re.finditer(
        r"^(PROMPT|RATIONALE|QUESTIONS|BOOSTER_SCAFFOLD|WHEN_TO_USE)\s*:\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    ):
        tags.append((m.group(1).upper(), m.end()))
    # If no standalone headers, try inline style
    if not tags:
        # Try to detect inline headers like "PROMPT:" followed by content
        for name in (
            "PROMPT",
            "RATIONALE",
            "QUESTIONS",
            "BOOSTER_SCAFFOLD",
            "WHEN_TO_USE",
        ):
            m = re.search(rf"{name}\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
            if m:
                out[name] = m.group(1).strip()
        return out
    # Collect sections
    tags.append(("__END__", len(text)))
    for i in range(len(tags) - 1):
        key = tags[i][0]
        body = text[tags[i][1] : tags[i + 1][1] - len(tags[i + 1][0]) - 1].strip()
        out[key] = body.strip()
    return out


async def prompt_boost(goal: str, ask: bool = True, meta: bool = False):
    global BOOST_PENDING, BOOST_LAST_PROMPT
    # Optionally fetch meta-scaffold (advisory only)
    scaffold = None
    if meta:
        SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
        set_system(repo_render("prompt.meta"))
        meta_reply = await send_and_collect(
            build_payload(f"USER GOAL:\n{goal}\n\nReturn only the scaffold."),
            silent=True,
        )
        if SAVE_SYSTEM_STACK:
            set_system(SAVE_SYSTEM_STACK.pop())
        meta_parts = _split_booster_sections(meta_reply)
        scaffold = meta_parts.get("BOOSTER_SCAFFOLD")

    # Run Booster
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_boost = repo_render("prompt.boost")
    if scaffold:
        sys_boost = sys_boost.strip() + "\n\nADVISORY SCAFFOLD (meta):\n" + scaffold
    set_system(sys_boost)

    user_msg = f"USER GOAL:\n{goal}\n\nIf info is missing, ask up to 5 concise questions; else produce PROMPT/RATIONALE now."
    reply = await send_and_collect(build_payload(user_msg))
    parts = _split_booster_sections(reply)
    BOOST_LAST_PROMPT = parts.get("PROMPT")

    if parts.get("QUESTIONS") and ask:
        # Hold pending Qs until user answers via /prompt.answer
        qs = [
            q.strip("- ").strip() for q in parts["QUESTIONS"].splitlines() if q.strip()
        ]
        BOOST_PENDING = {
            "goal": goal,
            "questions": qs,
            "system": sys_boost,
            "scaffold": scaffold,
        }
        ok("Booster has questions. Use /prompt.answer to provide answers.")
        print(hr())
        print("Questions:")
        for i, q in enumerate(qs, 1):
            print(f"  {i}. {q}")
        print(hr())
        if SAVE_SYSTEM_STACK:
            set_system(SAVE_SYSTEM_STACK.pop())
        return None

    if BOOST_LAST_PROMPT:
        ok("Booster produced a final prompt.")
        print(hr())
        print("PROMPT:\n" + BOOST_LAST_PROMPT)
        if parts.get("RATIONALE"):
            print("\nRATIONALE:\n" + parts["RATIONALE"])
        print(hr())
    else:
        warn("Booster did not return a PROMPT. See raw output above.")
    if SAVE_SYSTEM_STACK:
        set_system(SAVE_SYSTEM_STACK.pop())
    return BOOST_LAST_PROMPT


async def prompt_answer(answers_text: str):
    global BOOST_PENDING, BOOST_LAST_PROMPT
    if not BOOST_PENDING:
        warn("No pending booster questions.")
        return None
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    set_system(BOOST_PENDING["system"])
    payload = (
        "USER ANSWERS:\n" + answers_text.strip() + "\n\n"
        "Now produce the final improved prompt as:\nPROMPT: ...\nRATIONALE: ..."
    )
    reply = await send_and_collect(build_payload(payload))
    parts = _split_booster_sections(reply)
    BOOST_LAST_PROMPT = parts.get("PROMPT")
    if BOOST_LAST_PROMPT:
        ok("Applied answers. Booster produced a final prompt.")
        print(hr())
        print("PROMPT:\n" + BOOST_LAST_PROMPT)
        if parts.get("RATIONALE"):
            print("\nRATIONALE:\n" + parts["RATIONALE"])
        print(hr())
    else:
        warn("Booster could not create a prompt from answers.")
    BOOST_PENDING = None
    if SAVE_SYSTEM_STACK:
        set_system(SAVE_SYSTEM_STACK.pop())
    return BOOST_LAST_PROMPT


def prompt_apply(where: str = "next"):
    global BOOST_LAST_PROMPT, NEXT_OVERRIDE, SYSTEM_PROMPT
    if not BOOST_LAST_PROMPT:
        warn("No improved prompt available. Run /prompt.boost first.")
        return
    if where == "system":
        SYSTEM_PROMPT = BOOST_LAST_PROMPT
        ok("Improved prompt applied as SYSTEM for this session.")
    else:
        NEXT_OVERRIDE = BOOST_LAST_PROMPT
        ok("Improved prompt queued as the next user message.")


# ---------------- Recipe Runner Helpers ----------------
def _load_yaml_or_json(path: str) -> dict:
    try:
        import yaml  # type: ignore

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        with open(path, "r", encoding="utf-8") as f:
            import json

            return json.load(f)


def _apply_style_overlays(
    sys_text: str, styles: list[str] | None, style_file: str | None
) -> str:
    text = sys_text
    if styles:
        for s in styles:
            sv = s.strip().lower()
            if sv in ("no-bs", "nobs", "no_bs", "no-bullshit"):
                text = text.strip() + "\n\n" + NO_BS_ADDENDUM
            elif sv == "chad":
                text = text.strip() + "\n\n" + CHAD_TEMPLATE
        if style_file and os.path.exists(style_file):
            style = open(style_file, "r", encoding="utf-8").read()
            text = (
                text.strip() + "\n\nSTYLE OVERLAY:\n<<<STYLE\n" + style + "\nSTYLE>>>"
            )
        return text


async def run_recipe_file(path: str):
    rec = _load_yaml_or_json(path)
    await run_recipe(rec)


async def run_recipe(rec: dict):
    # Expected fields (all optional except task):
    # task, subject, styles[], style_file, hammer, continuation{}, io{}, custom_system_file, backend, model, max_chunks
    global AUTO_ON, AUTO_OUT, AUTO_MAX, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT
    global CONT_MODE, CONT_ANCHOR_CHARS, OUTPUT_MIN_CHARS, OUTPUT_PUSH_MAX_PASSES, REPEAT_WARN
    global COVERAGE_HAMMER_ON, BACKEND, MODEL_ID, SYSTEM_PROMPT

    task = rec.get("task")
    subject = rec.get("subject")
    styles = rec.get("styles") or rec.get("style") or []
    style_file = rec.get("style_file")
    hammer = bool(rec.get("hammer", True))
    cont = rec.get("continuation", {}) or {}
    io = rec.get("io", {}) or {}
    custom_system_file = rec.get("custom_system_file")
    backend = rec.get("backend")
    model = rec.get("model")
    max_chunks = rec.get("max_chunks")
    out_path = io.get("outPath") or io.get("out") or None

    # backend/model switches
    if backend in ("bridge", "openrouter"):
        globals()["BACKEND"] = backend
        ok(f"Backend set via recipe: {backend}")
    if model:
        globals()["MODEL_ID"] = model
        ok(f"Model set via recipe: {model}")

    # configure continuation knobs
    if "mode" in cont:
        globals()["CONT_MODE"] = cont["mode"]
    if "anchorLen" in cont:
        globals()["CONT_ANCHOR_CHARS"] = int(cont["anchorLen"])
    if "minChars" in cont:
        globals()["OUTPUT_MIN_CHARS"] = int(cont["minChars"])
    if "pushPasses" in cont:
        globals()["OUTPUT_PUSH_MAX_PASSES"] = int(cont["pushPasses"])
    if "repeatWarn" in cont:
        globals()["REPEAT_WARN"] = bool(cont["repeatWarn"])

    # hammer (coverage anti-wrap)
    globals()["COVERAGE_HAMMER_ON"] = bool(hammer)

    # base system from task
    if task in (
        "book.zero2hero",
        "book.reference",
        "book.pop",
        "exam.cram",
        "book.nobs",
    ):
        sys_text = repo_render(task, subject=subject or "Subject")
    elif task == "book.bilingual":
        sys_text = repo_render(
            "book.bilingual", subject=subject or "Subject", lang=rec.get("lang", "")
        )
    elif task == "lossless.rewrite":
        sys_text = PROMPT_REPO["book.lossless.rewrite"]["system"]
    elif task == "translate":
        sys_text = PROMPT_REPO["translate"]["system"].replace(
            "{lang}", rec.get("lang", "")
        )
    elif task == "answer.chad":
        sys_text = CHAD_TEMPLATE
    else:
        # default generic book/system
        sys_text = PROMPT_REPO.get(task, {}).get("system") or PROMPT_REPO[
            "book.zero2hero"
        ]["system"].replace("{subject}", subject or "Subject")

    # apply overlays
    sys_text = _apply_style_overlays(sys_text, styles, style_file)

    # custom system tail
    if custom_system_file and os.path.exists(custom_system_file):
        tail = open(custom_system_file, "r", encoding="utf-8").read()
        sys_text = sys_text.strip() + "\n\n" + tail

    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    set_system(sys_text.strip())
    if out_path:
        ensure_dir(os.path.dirname(out_path) or ".")
        globals()["AUTO_OUT"] = next_available_path(out_path)
    else:
        globals()["AUTO_OUT"] = None

    globals()["AUTO_ON"] = True
    globals()["AUTO_COUNT"] = 0
    globals()["LAST_NEXT_HINT"] = None
    globals()["AUTO_MAX"] = None if not max_chunks else int(max_chunks)
    ok(f"Recipe run started. Output → {AUTO_OUT or '(none)'}")
    if globals().get("AUTO_TASK") and not AUTO_TASK.done():
        AUTO_TASK.cancel()
    globals()["AUTO_TASK"] = asyncio.create_task(autorun_loop())


# ---------------- Book high-level modes ----------------
async def book_zero2hero(
    subject: str,
    plan_first: bool,
    outdir: str | None,
    max_chunks: int | None,
    window: int | None,
):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(os.path.join(outdir or BOOKS_DIR, f"{slug}.md"))
    outline_path = os.path.join(outdir or BOOKS_DIR, f"{slug}.outline.md")
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_text = repo_render("book.zero2hero", subject=subject)
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_text = sys_text.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(sys_text)
    SESSION_MODE = "zero2hero"
    if window is not None:
        set_window(window)
    if plan_first:
        plan_reply = await send_and_collect(build_payload(BOOK_PLAN_PROMPT))
        write_to_file(outline_path, plan_reply.strip())
        ok(f"Saved outline → {outline_path}")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path
    AUTO_ON = True
    AUTO_COUNT = 0
    LAST_NEXT_HINT = None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"Book autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done():
        AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())


async def book_reference(
    subject: str,
    plan_first: bool,
    outdir: str | None,
    max_chunks: int | None,
    window: int | None,
):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(
        os.path.join(outdir or BOOKS_DIR, f"{slug}.reference.md")
    )
    outline_path = os.path.join(outdir or BOOKS_DIR, f"{slug}.reference.outline.md")
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_text = repo_render("book.reference", subject=subject)
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_text = sys_text.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(sys_text)
    if window is not None:
        set_window(window)
    if plan_first:
        plan = "Sketch the top-level sections and subsections for the reference handbook. End with NEXT: [Start Section 1]."
        plan_reply = await send_and_collect(build_payload(plan))
        write_to_file(outline_path, plan_reply.strip())
        ok(f"Saved outline → {outline_path}")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path
    AUTO_ON = True
    AUTO_COUNT = 0
    LAST_NEXT_HINT = None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"Reference autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done():
        AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())


async def book_pop(
    subject: str,
    plan_first: bool,
    outdir: str | None,
    max_chunks: int | None,
    window: int | None,
):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(os.path.join(outdir or BOOKS_DIR, f"{slug}.pop.md"))
    outline_path = os.path.join(outdir or BOOKS_DIR, f"{slug}.pop.outline.md")
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_text = repo_render("book.pop", subject=subject)
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_text = sys_text.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(sys_text)
    if window is not None:
        set_window(window)
    if plan_first:
        plan = "Draft a compelling, accurate chapter plan for the pop-science book. One line per chapter goal. End with NEXT: [Begin Chapter 1]."
        plan_reply = await send_and_collect(build_payload(plan))
        write_to_file(outline_path, plan_reply.strip())
        ok(f"Saved outline → {outline_path}")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path
    AUTO_ON = True
    AUTO_COUNT = 0
    LAST_NEXT_HINT = None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"Pop-science autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done():
        AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())


async def exam_cram(
    subject: str, outdir: str | None, max_chunks: int | None, window: int | None
):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(os.path.join(outdir or BOOKS_DIR, f"{slug}.cram.md"))
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_text = repo_render("exam.cram", subject=subject)
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_text = sys_text.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(sys_text)
    if window is not None:
        set_window(window)
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path
    AUTO_ON = True
    AUTO_COUNT = 0
    LAST_NEXT_HINT = None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"Exam-cram autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done():
        AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())


async def book_nobs(
    subject: str,
    plan_first: bool,
    outdir: str | None,
    max_chunks: int | None,
    window: int | None,
):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(os.path.join(outdir or BOOKS_DIR, f"{slug}.nobs.md"))
    outline_path = os.path.join(outdir or BOOKS_DIR, f"{slug}.nobs.outline.md")
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_text = repo_render("book.nobs", subject=subject)
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_text = sys_text.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(sys_text)
    if window is not None:
        set_window(window)
    if plan_first:
        plan = "Draft a compact outline of the essentials. Only sections that change decisions or understanding. End with NEXT: [Begin]."
        plan_reply = await send_and_collect(build_payload(plan))
        write_to_file(outline_path, plan_reply.strip())
        ok(f"Saved outline → {outline_path}")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path
    AUTO_ON = True
    AUTO_COUNT = 0
    LAST_NEXT_HINT = None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"No‑bullshit autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done():
        AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())


# NEW: Bilingual book function
async def book_bilingual(
    subject: str,
    lang: str,
    plan_first: bool,
    outdir: str | None,
    max_chunks: int | None,
    window: int | None,
):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(
        os.path.join(outdir or BOOKS_DIR, f"{slug}.bilingual.md")
    )
    outline_path = os.path.join(outdir or BOOKS_DIR, f"{slug}.bilingual.outline.md")
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_text = repo_render("book.bilingual", subject=subject, lang=lang)
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_text = sys_text.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(sys_text)
    if window is not None:
        set_window(window)
    if plan_first:
        plan = f"Create a chapter outline for a bilingual book on {subject} in English and {lang}. End with NEXT: [Begin Chapter 1]."
        plan_reply = await send_and_collect(build_payload(plan))
        write_to_file(outline_path, plan_reply.strip())
        ok(f"Saved outline → {outline_path}")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path
    AUTO_ON = True
    AUTO_COUNT = 0
    LAST_NEXT_HINT = None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"Bilingual book autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done():
        AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())


# NEW: Bilingual transform function
async def bilingual_transform_file(path: str, lang: str, outdir=None, chunk_kb=45):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    outdir = outdir or BOOKS_DIR
    ensure_dir(outdir)
    base = slugify(os.path.splitext(os.path.basename(path))[0])
    out_path = next_available_path(os.path.join(outdir, f"{base}.bilingual.md"))

    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    set_system(repo_render("bilingual.transform", lang=lang))
    set_window(0)

    try:
        parts = chunks_by_bytes(text, max(10_000, chunk_kb * 1024))
        for i, chunk in enumerate(parts, 1):
            reply = await send_and_collect(build_payload(chunk), silent=True)
            write_to_file(out_path, reply.strip())
            print(f"[{now()}] Bilingual transform {i}/{len(parts)}")
        ok(f"Bilingual transform → {out_path}")
    finally:
        set_system(SAVE_SYSTEM_STACK.pop())
        set_window(40)


# NEW: Policy generator function
async def policy_from_regulations(
    reg_file: str,
    out_dir: str,
    org=None,
    jurisdiction=None,
    chunk_kb=45,
    synth_chars=16000,
):
    ensure_dir(out_dir)
    with open(reg_file, "r", encoding="utf-8") as f:
        reg_text = f.read()

    base = slugify(os.path.splitext(os.path.basename(reg_file))[0])
    synth_path = os.path.join(out_dir, f"{base}.policy.synth.md")

    # First, generate synthesis from regulations
    await ingest_synth_loop(reg_file, synth_path, chunk_kb, synth_chars)

    # Then generate policy docs using the synthesis
    org_text = f" for {org}" if org else ""
    juris_text = f" in {jurisdiction}" if jurisdiction else ""

    policy_system = repo_render("policy.generator")
    policy_system += f"\n\nREGULATORY CONTEXT: The policy should address the regulations specified in '{reg_file}'{org_text}{juris_text}."

    # Generate policy
    policy_path = next_available_path(os.path.join(out_dir, f"{base}.policy.md"))
    await chunked_generate_with_system(synth_path, policy_system, policy_path)


# ---------------- Study helpers ----------------
async def flashcards_from_synth(
    synth_path: str, out_path: str, n: int = 200, mode: str = "anki"
):
    synth = open(synth_path, "r", encoding="utf-8").read()
    fmt = "Q: ...\nA: ...\n---" if mode == "anki" else "- Question: ...\n  Answer: ..."
    prompt = (
        f"From this synthesis, generate {n} high-quality study cards.\n"
        f"Format: {fmt}\n"
        "Focus on decisions, definitions, formulas, and pitfalls.\n"
        "SYNTHESIS:\n<<<S\n" + synth + "\nS>>>"
    )
    reply = await send_and_collect(build_payload(prompt))
    write_to_file(out_path, reply.strip())
    ok(f"Flashcards → {out_path}")


async def glossary_from_synth(synth_path: str, out_path: str):
    synth = open(synth_path, "r", encoding="utf-8").read()
    prompt = (
        "Extract a glossary of terms (A–Z) with tight definitions and a one-line why-it-matters.\nSYNTHESIS:\n<<<S\n"
        + synth
        + "\nS>>>"
    )
    reply = await send_and_collect(build_payload(prompt))
    write_to_file(out_path, reply.strip())
    ok(f"Glossary → {out_path}")


async def index_from_synth(synth_path: str, out_path: str):
    synth = open(synth_path, "r", encoding="utf-8").read()
    prompt = (
        "Create an index-like map of topics/subtopics for quick lookup. Group related items.\nSYNTHESIS:\n<<<S\n"
        + synth
        + "\nS>>>"
    )
    reply = await send_and_collect(build_payload(prompt))
    write_to_file(out_path, reply.strip())
    ok(f"Index → {out_path}")


async def answer_chad(
    question: str,
    depth: str = "short",
    bullets: bool = True,
    refs: bool = True,
    contra: bool = True,
):
    """
    One-shot Chad answer:
      depth: short | medium | deep
      bullets: True = bullet list; False = prose (tight paragraphs)
      refs: True = name canonical sources lightly; False = no refs
      contra: True = brief steelman opposing view before conclusion
    """
    # Push current system and set Chad system
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    set_system(PROMPT_REPO["answer.chad"]["system"])

    # Build user directive with flags
    fmt = "Bulleted points" if bullets else "Tight prose paragraphs (1–3)"
    depth_map = {
        "short": "Aim for ~6–10 lines.",
        "medium": "Aim for ~12–18 lines.",
        "deep": "Aim for ~20–30 lines; still concise.",
    }
    depth_instr = depth_map.get(depth.lower(), depth_map["short"])
    refs_instr = (
        "Name canonical sources lightly in-text." if refs else "Do not name sources."
    )
    contra_instr = (
        "Briefly steelman main opposing view, then decide."
        if contra
        else "Skip opposing view."
    )

    user = (
        f"FORMAT: {fmt}. {depth_instr} {refs_instr} {contra_instr}\n"
        "QUESTION:\n<<<Q\n" + question.strip() + "\nQ>>>"
    )
    # Ask once and restore system
    try:
        reply = await send_and_collect(build_payload(user))
        # Optionally, show a separator and store in history for continuity
        print(hr())
        HISTORY.append({"role": "user", "content": user})
        HISTORY.append({"role": "assistant", "content": reply})
        return reply
    finally:
        if SAVE_SYSTEM_STACK:
            set_system(SAVE_SYSTEM_STACK.pop())


async def translate_file(path: str, lang: str, chunk_kb: int = 50):
    tpl = PROMPT_REPO["translate"]["system"].replace("{lang}", lang)
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    set_system(tpl)
    set_window(0)
    try:
        text = open(path, "r", encoding="utf-8").read()
        parts = chunks_by_bytes(text, max(10_000, chunk_kb * 1024))
        base = os.path.splitext(os.path.basename(path))[0]
        out_path = next_available_path(
            os.path.join(BOOKS_DIR, f"{slugify(base)}-{slugify(lang)}.md")
        )
        for i, chunk in enumerate(parts, 1):
            reply = await send_and_collect(build_payload(chunk), silent=True)
            write_to_file(out_path, reply.strip())
            print(f"[{now()}] Translated {i}/{len(parts)}")
        ok(f"Translated file → {out_path}")
    finally:
        set_system(SAVE_SYSTEM_STACK.pop())
        set_window(40)


# ---------------- Style apply ----------------
async def style_apply(
    style_path: str, topic_or_file: str, out_path: str | None, max_words: int | None
):
    style = open(style_path, "r", encoding="utf-8").read()
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    set_system(PROMPT_REPO["style.transfer"]["system"].replace("{style}", style))
    if os.path.exists(topic_or_file):
        text = open(topic_or_file, "r", encoding="utf-8").read()
        user = f"Rewrite the following content in the captured style. Keep meaning intact.\n<<<CONTENT\n{text}\nCONTENT>>>"
    else:
        user = f"Write in the captured style about: {topic_or_file}"
    if max_words:
        user += f"\nTarget length: ~{max_words} words."
    reply = await send_and_collect(build_payload(user))
    if out_path:
        write_to_file(out_path, reply.strip())
        ok(f"Wrote → {out_path}")
    if SAVE_SYSTEM_STACK:
        set_system(SAVE_SYSTEM_STACK.pop())


# ---------------- Lossless pipeline ----------------
async def rewrite_lossless(synth_path: str, out_path: str | None = None):
    base = slugify(os.path.splitext(os.path.basename(synth_path))[0])
    if out_path is None:
        out_path = next_available_path(os.path.join(BOOKS_DIR, f"{base}.lossless.md"))
    sys_template = PROMPT_REPO["book.lossless.rewrite"]["system"]
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_template = sys_template.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    await rewrite_start(synth_path, out_path, system_template=sys_template)


async def lossless_run(
    path: str, outdir: str | None = None, chunk_kb: int = 45, synth_chars: int = 12000
):
    outdir = outdir or BOOKS_DIR
    ensure_dir(outdir)
    base = slugify(os.path.splitext(os.path.basename(path))[0])
    synth_path = os.path.join(outdir, f"{base}.lossless.synth.md")
    await ingest_synth_loop(path, synth_path, chunk_kb, synth_chars)
    await rewrite_lossless(synth_path, os.path.join(outdir, f"{base}.lossless.md"))


# ---------------- Helpers to tweak runtime ----------------
def set_system(text: str):
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = text or ""


def set_window(n: int):
    global HISTORY_WINDOW
    HISTORY_WINDOW = max(0, int(n))


# ---------------- CLI loop ----------------
def help_text():
    print(hr())
    info("Minimal LMArena CLI — Prompt Studio")
    print("Core:")
    print("  /help                 Show this help")
    print("  /status               Show state")
    print("  /capture              Capture IDs (then click Retry in LMArena)")
    print("  /setids <sess> <msg>  Set IDs manually")
    print("  /showids              Show IDs")
    print("Project & Pipeline:")
    print(
        "  /project.init [--dir=.]        Scaffold .lmastudio/, pipelines/, recipes/, etc."
    )
    print(
        "  /pipeline.run <pipeline.yml>   Execute a multi-step workflow (synth -> rewrite -> ...)"
    )
    print("Prompt repo:")
    print("  /repo.list")
    print("  /repo.show <key> [n]")
    print("  /repo.use <key> [args]      (advanced)")
    print("Books (subject-aware):")
    print("  /book.zero2hero <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]")
    print("  /book.reference <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]")
    print("  /book.nobs <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]")
    print("  /book.pop <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]")
    print(
        "  /book.bilingual <subject> --lang=LANG [--plan] [--max=N] [--window=N] [--outdir=DIR]"
    )
    print("  /exam.cram <subject> [--max=N] [--window=N] [--outdir=DIR]")
    print("Autopilot control:")
    print(
        "  /book.pause | /book.resume | /next <text>   (one-shot override for the next prompt)"
    )
    print(
        "  /book.hammer on|off               Toggle strict no-wrap continuation hint for self-study"
    )
    print(
        "  /book.save [name]                 Save current autopilot state to checkpoint"
    )
    print("  /book.load <name>                 Load autopilot state from checkpoint")
    print("  /book.start <out.md>              Start manual autopilot (no template)")
    print("  /book.stop | /book.max <N>        Stop or set max chunks")
    print("Output budget:")
    print(
        "  /out.budget on|off                 Append OUTPUT BUDGET addendum to book prompts (default on)"
    )
    print(
        "  /out.push on|off                   Auto-extend within a subtopic to hit min length (default on)"
    )
    print(
        "  /out.minchars <N>                  Set minimal chars per chunk before moving on (default 4500)"
    )
    print(
        "  /out.passes <N>                    Max extension steps per chunk (default 3)"
    )
    print("  /cf.status | /cf.resume | /cf.reset Show/control Cloudflare pause")
    print(
        "  /cont.mode [normal|anchor]        Set continuation strategy (default: anchor)"
    )
    print(
        "  /cont.anchor <N>                  Set anchor length in chars (default 200)"
    )
    print("  /repeat.warn on|off               Toggle repetition warning (default on)")
    print(
        "  /repeat.thresh <0..1>            Set repetition Jaccard threshold (default 0.35)"
    )
    print("Ingestion/Synthesis/Style:")
    print("  /ingest.ack <file> [chunkKB=80]")
    print("  /ingest.synth <file> <synth.md> [chunkKB=45] [synthChars=9500]")
    print("  /ingest.lossless <file> <synth.md> [chunkKB=45] [synthChars=12000]")
    print("  /style.capture <file> <style.synth.md> [chunkKB=30] [styleChars=6000]")
    print("  /style.apply <style.synth.md> <topic|file> [out.md] [--words=N]")
    print("Rewrite:")
    print("  /rewrite.start <synth.md> <out.md>")
    print("  /rewrite.lossless <synth.md> [out.md]")
    print("One-shot pipeline:")
    print("  /lossless.run <file> [--outdir=DIR] [--chunkKB=45] [--synthChars=12000]")
    print("Special tools:")
    print("  /bilingual.file <file> --lang=LANG [--outdir=DIR] [--chunkKB=45]")
    print(
        "  /policy.from <reg_file> <out_dir> [--org='...'] [--jurisdiction='...'] [--chunkKB=45] [--synthChars=16000]"
    )
    print("Study/Translate:")
    print("  /flashcards.from <synth.md> <out.md> [n=200]")
    print("  /glossary.from <synth.md> <out.md>")
    print("  /index.from <synth.md> <out.md>")
    print("  /translate.file <file> <language> [chunkKB=50]")
    print("Q&A:")
    print(
        '  /chad "<question>" [--depth=short|medium|deep] [--prose] [--norefs] [--nocontra]'
    )
    print("Prompt Booster:")
    print('  /prompt.boost "goal" [--ask] [--apply] [--meta]')
    print(
        "  /prompt.answer                 (answer booster questions; end paste with EOF)"
    )
    print("  /prompt.apply [next|system]    (apply improved prompt)")
    print("Recipes:")
    print("  /run.recipe <recipe.json|yml>")
    print('  /run.quick task=... subject="..." out=path [max=N] [style=no-bs,chad]')
    print("Macros:")
    print('  /macro.save <name> "<command template>"')
    print("  /macro.list | /macro.delete <name>")
    print("  /macro.run <name> [arg1 arg2 ...]")
    print("Snapshot:")
    print(
        "  /snapshot [--chunk]            Create snapshot.txt (or chunks) via snapshot.sh"
    )
    print("Prompt & Model:")
    print(
        "  /system <line> | /systemfile <path> | /system.append (paste, end with EOF)"
    )
    print(
        "  /style.nobs on|off                  Harden language (plain, no fluff) for current session"
    )
    print(
        "  /style.narrative on|off            Narrative + pedagogy overlay (teach-before-use, vignettes, quick checks)"
    )
    print("  /model <uuid|none> | /window <N> | /history.tail | /mono | /clear")
    print(
        "  /image on|off                     Toggle markdown images from a2 image streams (default on)"
    )
    print("  /debug.cont | /debug.ctx")
    print("OpenRouter:")
    print("  /backend bridge|openrouter          Switch backend")
    print("  /or.model <model>                  Set OpenRouter model")
    print("  /or.ref <url> | /or.title <text>   Set optional headers")
    print("  /or.status                         Show OpenRouter status")
    print("  /exit                              Exit the CLI")
    print(hr())


def show_status():
    info("Status:")
    print(f"  Browser polling: {'yes' if CLIENT_SEEN else 'no'}")
    print(f"  IDs: session={SESSION_ID or '-'} message={MESSAGE_ID or '-'}")
    print(
        f"  Model: {MODEL_ID or '(session default)'}   History window: {HISTORY_WINDOW}"
    )
    print(f"  System directive set: {'yes' if SYSTEM_PROMPT.strip() else 'no'}")
    print(
        f"  Ingest: {'ON' if ING_ON else 'OFF'} mode={ING_MODE or '-'} pos={ING_POS}/{ING_TOTAL} file={os.path.basename(ING_PATH) if ING_PATH else '-'}  synth_out={SYNTH_OUT or '-'}"
    )
    print(
        f"  Autopilot: {'ON' if AUTO_ON else 'OFF'} paused={AUTO_PAUSE} chunks={AUTO_COUNT} next={LAST_NEXT_HINT or '-'} out={AUTO_OUT or '-'}"
    )


def prompt():
    print(f"{C.INFO}> {C.R}", end="", flush=True)


async def read_multiline(hint="Paste lines. End with: EOF"):
    print(hint)
    buf = []
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        if line.strip() == "EOF":
            break
        buf.append(line.rstrip("\n"))
    return "\n".join(buf)


async def _handle_command(line):
    global CAPTURE_FLAG, SESSION_ID, MESSAGE_ID, SYSTEM_PROMPT, MODEL_ID
    global AUTO_ON, AUTO_TASK, AUTO_OUT, AUTO_MAX, AUTO_COUNT, LAST_NEXT_HINT, NEXT_OVERRIDE, AUTO_PAUSE
    global ING_ON, ING_TASK, ING_MODE, ING_PATH, ING_POS, ING_TOTAL, ING_CHUNK_BYTES, SYNTH_LIMIT, SYNTH_OUT
    global BACKEND, OR_MODEL, OR_REFERRER, OR_TITLE
    global COVERAGE_HAMMER_ON, OUTPUT_BUDGET_SNIPPET_ON, OUTPUT_PUSH_ON, OUTPUT_MIN_CHARS, OUTPUT_PUSH_MAX_PASSES, CONT_MODE, CONT_ANCHOR_CHARS

    if line.startswith("/"):
        parts = line.split(" ", 2)
        cmd = parts[0].lower()

        # Core
        if cmd == "/help":
            help_text()
        elif cmd == "/exit":
            print("Bye.")
            raise SystemExit(0)
        elif cmd == "/status":
            show_status()
        elif cmd == "/capture":
            CAPTURE_FLAG = True
            ok("Capture ON. Click Retry in LMArena.")
        elif cmd == "/setids" and len(parts) >= 3:
            SESSION_ID, MESSAGE_ID = parts[1], parts[2]
            ok("IDs set.")
        elif cmd == "/showids":
            print(
                f"session_id={SESSION_ID or '(unset)'}\nmessage_id={MESSAGE_ID or '(unset)'}"
            )

        # Repo
        elif cmd == "/repo.list":
            print(repo_list())
        elif cmd == "/repo.show":
            toks = line.split()
            if len(toks) < 2:
                err("Usage: /repo.show <key> [n]")
            else:
                key = toks[1]
                if key not in PROMPT_REPO:
                    err("Unknown key.")
                else:
                    n = int(toks[2]) if len(toks) >= 3 and toks[2].isdigit() else 500
                    text = PROMPT_REPO[key]["system"]
                    print((text[:n] + ("..." if len(text) > n else "")))
        elif cmd == "/repo.use":
            toks = line.split()
            if len(toks) < 2:
                err("Usage: /repo.use <key> [args]")
                prompt()
                return
            key = toks[1]
            if key not in PROMPT_REPO:
                err("Unknown repo key.")
                prompt()
                return
            if key == "translate":
                if len(toks) < 3:
                    err("Usage: /repo.use translate <lang>")
                    prompt()
                    return
                set_system(repo_render("translate", lang=" ".join(toks[2:])))
                ok("Translator system set.")
            elif key == "brainstorm":
                set_system(repo_render("brainstorm"))
                ok("Brainstorm system set.")
            elif key in (
                "book.zero2hero",
                "book.reference",
                "book.pop",
                "exam.cram",
                "book.bilingual",
            ):
                if len(toks) < 3:
                    err(f"Usage: /repo.use {key} <subject>")
                    prompt()
                    return
                if key == "book.bilingual":
                    # Special case for bilingual - needs lang
                    subject = toks[2]
                    lang = None
                    for tk in toks[3:]:
                        if tk.startswith("--lang="):
                            lang = tk.split("=", 1)[1]
                            break
                    if not lang:
                        err("For /repo.use book.bilingual, provide --lang=LANG")
                        prompt()
                        return
                    set_system(repo_render(key, subject=subject, lang=lang))
                else:
                    set_system(repo_render(key, subject=" ".join(toks[2:])))
                ok(f"{key} system set.")
            elif key == "book.lossless.rewrite":
                set_system(PROMPT_REPO[key]["system"])
                ok("Lossless rewrite system set.")
            else:
                set_system(PROMPT_REPO[key]["system"])
                ok(f"{key} system set.")

        # Subject-aware book modes
        elif cmd == "/book.zero2hero":
            if len(parts) < 2:
                err(
                    "Usage: /book.zero2hero <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"
                )
                prompt()
                return
            tokens = line.split()[1:]
            subject_tokens = []
            plan = False
            maxc = None
            wind = None
            outdir = None
            for tk in tokens:
                if tk == "--plan":
                    plan = True
                elif tk.startswith("--max="):
                    try:
                        maxc = int(tk.split("=", 1)[1])
                    except:
                        pass
                elif tk.startswith("--window="):
                    try:
                        wind = int(tk.split("=", 1)[1])
                    except:
                        pass
                elif tk.startswith("--outdir="):
                    outdir = tk.split("=", 1)[1]
                elif tk.startswith("--"):
                    pass
                else:
                    subject_tokens.append(tk)
            if not subject_tokens:
                err("Provide a subject, e.g., /book.zero2hero Psychology")
                prompt()
                return
            await book_zero2hero(" ".join(subject_tokens), plan, outdir, maxc, wind)

        elif cmd == "/book.reference":
            if len(parts) < 2:
                err(
                    "Usage: /book.reference <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"
                )
                prompt()
                return
            tokens = line.split()[1:]
            subject_tokens = []
            plan = False
            maxc = None
            wind = None
            outdir = None
            for tk in tokens:
                if tk == "--plan":
                    plan = True
                elif tk.startswith("--max="):
                    try:
                        maxc = int(tk.split("=", 1)[1])
                    except:
                        pass
                elif tk.startswith("--window="):
                    try:
                        wind = int(tk.split("=", 1)[1])
                    except:
                        pass
                elif tk.startswith("--outdir="):
                    outdir = tk.split("=", 1)[1]
                elif tk.startswith("--"):
                    pass
                else:
                    subject_tokens.append(tk)
            if not subject_tokens:
                err("Provide a subject.")
                prompt()
                return
            await book_reference(" ".join(subject_tokens), plan, outdir, maxc, wind)

        elif cmd == "/book.pop":
            if len(parts) < 2:
                err(
                    "Usage: /book.pop <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"
                )
                prompt()
                return
            tokens = line.split()[1:]
            subject_tokens = []
            plan = False
            maxc = None
            wind = None
            outdir = None
            for tk in tokens:
                if tk == "--plan":
                    plan = True
                elif tk.startswith("--max="):
                    try:
                        maxc = int(tk.split("=", 1)[1])
                    except:
                        pass
                elif tk.startswith("--window="):
                    try:
                        wind = int(tk.split("=", 1)[1])
                    except:
                        pass
                elif tk.startswith("--outdir="):
                    outdir = tk.split("=", 1)[1]
                elif tk.startswith("--"):
                    pass
                else:
                    subject_tokens.append(tk)
            if not subject_tokens:
                err("Provide a subject.")
                prompt()
                return
            await book_pop(" ".join(subject_tokens), plan, outdir, maxc, wind)

        elif cmd == "/exam.cram":
            if len(parts) < 2:
                err("Usage: /exam.cram <subject> [--max=N] [--window=N] [--outdir=DIR]")
                prompt()
                return
            tokens = line.split()[1:]
            subject_tokens = []
            maxc = None
            wind = None
            outdir = None
            for tk in tokens:
                if tk.startswith("--max="):
                    try:
                        maxc = int(tk.split("=", 1)[1])
                    except:
                        pass
                elif tk.startswith("--window="):
                    try:
                        wind = int(tk.split("=", 1)[1])
                    except:
                        pass
                elif tk.startswith("--outdir="):
                    outdir = tk.split("=", 1)[1]
                elif tk.startswith("--"):
                    pass
                else:
                    subject_tokens.append(tk)
            if not subject_tokens:
                err("Provide a subject.")
                prompt()
                return
            await exam_cram(" ".join(subject_tokens), outdir, maxc, wind)

        elif cmd == "/book.bilingual":
            tokens = line.split()[1:]
            subject_tokens = []
            plan = False
            maxc = None
            wind = None
            outdir = None
            lang = None
            for tk in tokens:
                if tk == "--plan":
                    plan = True
                elif tk.startswith("--lang="):
                    lang = tk.split("=", 1)[1]
                elif tk.startswith("--max="):
                    maxc = int(tk.split("=", 1)[1])
                elif tk.startswith("--window="):
                    wind = int(tk.split("=", 1)[1])
                elif tk.startswith("--outdir="):
                    outdir = tk.split("=", 1)[1]
                elif tk.startswith("--"):
                    pass
                else:
                    subject_tokens.append(tk)
            if not subject_tokens or not lang:
                err(
                    "Usage: /book.bilingual <subject> --lang=LANG [--plan] [--max=N] [--window=N] [--outdir=DIR]"
                )
            else:
                await book_bilingual(
                    " ".join(subject_tokens), lang, plan, outdir, maxc, wind
                )

        elif cmd == "/book.pause":
            AUTO_PAUSE = True
            ok("Autopilot pause requested.")
        elif cmd == "/book.resume":
            AUTO_PAUSE = False
            ok("Autopilot resume requested.")
        elif cmd == "/book.stop":
            AUTO_ON = False
            AUTO_TASK = None
            ok("Autopilot stopped.")
            if AUTO_OUT:
                print(f"(output saved to {AUTO_OUT})")

        elif cmd == "/book.hammer":
            if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                COVERAGE_HAMMER_ON = parts[1].strip().lower() == "on"
                ok(f"Self-study continuation hammer: {COVERAGE_HAMMER_ON}")
            else:
                err("Usage: /book.hammer on|off")

        elif cmd == "/out.budget":
            if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                OUTPUT_BUDGET_SNIPPET_ON = parts[1].strip().lower() == "on"
                ok(f"OUTPUT_BUDGET addendum: {OUTPUT_BUDGET_SNIPPET_ON}")
            else:
                err("Usage: /out.budget on|off")

        elif cmd == "/out.push":
            if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                OUTPUT_PUSH_ON = parts[1].strip().lower() == "on"
                ok(f"Output push: {OUTPUT_PUSH_ON}")
            else:
                err("Usage: /out.push on|off")

        elif cmd == "/out.minchars":
            if len(parts) >= 2:
                try:
                    v = int(parts[1])
                    if v < 1000:
                        warn("Value too small; suggest >= 2500.")
                    OUTPUT_MIN_CHARS = max(1000, v)
                    ok(f"OUTPUT_MIN_CHARS={OUTPUT_MIN_CHARS}")
                except:
                    err("Provide an integer.")
            else:
                err("Usage: /out.minchars <N>")

        elif cmd == "/out.passes":
            if len(parts) >= 2:
                try:
                    v = int(parts[1])
                    if v < 0 or v > 10:
                        warn("Unusual value; using within [0..10].")
                    OUTPUT_PUSH_MAX_PASSES = max(0, min(10, v))
                    ok(f"OUTPUT_PUSH_MAX_PASSES={OUTPUT_PUSH_MAX_PASSES}")
                except:
                    err("Provide an integer.")
            else:
                err("Usage: /out.passes <N>")

        elif cmd == "/cont.mode":
            if len(parts) >= 2 and parts[1].strip().lower() in ("normal", "anchor"):
                CONT_MODE = parts[1].strip().lower()
                ok(f"Continuation mode: {CONT_MODE}")
            else:
                err("Usage: /cont.mode [normal|anchor]")

        elif cmd == "/cont.anchor":
            if len(parts) >= 2:
                try:
                    n = int(parts[1])
                    if n < 50 or n > 2000:
                        warn("Choose a value between 50 and 2000.")
                    else:
                        CONT_ANCHOR_CHARS = n
                        ok(f"Anchor length: {CONT_ANCHOR_CHARS}")
                except:
                    err("Provide an integer.")
            else:
                err("Usage: /cont.anchor <N>")

        elif cmd == "/book.max":  # legacy alias
            if len(parts) >= 2 and parts[1].isdigit():
                AUTO_MAX = int(parts[1])
                ok(f"Autopilot max chunks: {AUTO_MAX}")
            else:
                err("Usage: /book.max <N>")

        elif cmd == "/auto.max":
            if len(parts) >= 2 and parts[1].isdigit():
                AUTO_MAX = int(parts[1])
                ok(f"Autopilot max chunks: {AUTO_MAX}")
            else:
                err("Usage: /auto.max <N>")

        elif cmd == "/auto.out":
            if len(parts) >= 2:
                AUTO_OUT = " ".join(parts[1:])
                ok(f"Autopilot output: {AUTO_OUT}")
            else:
                err("Usage: /auto.out <file>")

        elif cmd == "/ingest.synth":
            if len(parts) >= 2:
                ING_PATH = " ".join(parts[1:])
                ING_MODE = "synth"
                await _ingest_loop()
                ok(f"Synth ingest started on: {ING_PATH}")
            else:
                err("Usage: /ingest.synth <file>")

        elif cmd == "/ingest.file":
            if len(parts) >= 2:
                ING_PATH = " ".join(parts[1:])
                ING_MODE = "file"
                await _ingest_loop()
                ok(f"File ingest started on: {ING_PATH}")
            else:
                err("Usage: /ingest.file <file>")

        elif cmd == "/ingest.pause":
            ING_ON = False
            ok("Ingest paused.")
        elif cmd == "/ingest.resume":
            if ING_PATH and ING_MODE:
                ING_ON = True
                ok("Ingest resumed.")
            else:
                err("No ingest in progress. Use /ingest.file or /ingest.synth first.")
        elif cmd == "/ingest.stop":
            ING_ON = False
            ING_PATH = None
            ING_MODE = None
            ok("Ingest stopped.")

        elif cmd == "/ingest.chunk":
            if len(parts) >= 2 and parts[1].isdigit():
                ING_CHUNK_BYTES = int(parts[1])
                ok(f"Ingest chunk size: {ING_CHUNK_BYTES} bytes")
            else:
                err("Usage: /ingest.chunk <bytes>")

        elif cmd == "/ingest.pos":
            if len(parts) >= 2 and parts[1].isdigit():
                ING_POS = int(parts[1])
                ok(f"Ingest position: {ING_POS}")
            else:
                err("Usage: /ingest.pos <N>")

        elif cmd == "/synth.limit":
            if len(parts) >= 2 and parts[1].isdigit():
                SYNTH_LIMIT = int(parts[1])
                ok(f"Synth limit: {SYNTH_LIMIT} chars")
            else:
                err("Usage: /synth.limit <N>")

        elif cmd == "/synth.out":
            if len(parts) >= 2:
                SYNTH_OUT = " ".join(parts[1:])
                ok(f"Synth output: {SYNTH_OUT}")
            else:
                err("Usage: /synth.out <file>")

        elif cmd == "/flashcards.from":
            if len(parts) >= 2:
                await _flashcards_from(" ".join(parts[1:]))
            else:
                err("Usage: /flashcards.from <file_or_url>")

        elif cmd == "/glossary.from":
            if len(parts) >= 2:
                await _glossary_from(" ".join(parts[1:]))
            else:
                err("Usage: /glossary.from <file_or_url>")

        elif cmd == "/index.from":
            if len(parts) >= 2:
                await _index_from(" ".join(parts[1:]))
            else:
                err("Usage: /index.from <file_or_url>")

        elif cmd == "/translate.file":
            toks = line.split()
            if len(toks) < 2:
                err("Usage: /translate.file <file> <language> [chunkKB=50]")
                prompt()
                return
            filepath = toks[1]
            if len(toks) < 3:
                err("Usage: /translate.file <file> <language> [chunkKB=50]")
                prompt()
                return
            language = toks[2]
            chunk_kb = int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 50
            await _translate_file(filepath, language, chunk_kb)

        elif cmd == "/style.capture":
            if len(parts) >= 2:
                STYLE_CAPTURE_FILE = " ".join(parts[1:])
                await _style_capture(STYLE_CAPTURE_FILE)
            else:
                err("Usage: /style.capture <file>")

        elif cmd == "/style.apply":
            if len(parts) >= 2:
                content = " ".join(parts[1:])
                result = await _style_apply(content)
                print(result)
            else:
                err("Usage: /style.apply <content>")

        elif cmd == "/style.nobs":
            if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                val = parts[1].strip().lower()
                global NO_BS_ACTIVE
                if val == "on" and not NO_BS_ACTIVE:
                    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
                    set_system(
                        (SYSTEM_PROMPT.strip() + "\n\n" + NO_BS_ADDENDUM).strip()
                    )
                    NO_BS_ACTIVE = True
                    ok("No‑bullshit language ON (session).")
                elif val == "off" and NO_BS_ACTIVE:
                    if SAVE_SYSTEM_STACK:
                        set_system(SAVE_SYSTEM_STACK.pop())
                    NO_BS_ACTIVE = False
                    ok("No‑bullshit language OFF.")
                else:
                    warn("Already in desired state.")
            else:
                err("Usage: /style.nobs on|off")
            return

        elif cmd == "/style.narrative":
            if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                val = parts[1].strip().lower()
                global NARRATIVE_ACTIVE
                if val == "on" and not NARRATIVE_ACTIVE:
                    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
                    set_system(
                        (SYSTEM_PROMPT.strip() + "\n\n" + NARRATIVE_OVERLAY).strip()
                    )
                    NARRATIVE_ACTIVE = True
                    ok("Narrative + pedagogy overlay ON (session).")
                elif val == "off" and NARRATIVE_ACTIVE:
                    if SAVE_SYSTEM_STACK:
                        set_system(SAVE_SYSTEM_STACK.pop())
                    NARRATIVE_ACTIVE = False
                    ok("Narrative + pedagogy overlay OFF.")
                else:
                    warn("Already in desired state.")
            else:
                err("Usage: /style.narrative on|off")
            return

        # Density and continuation knobs (exposed in PTK path as well)
        elif cmd == "/book.hammer":
            if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                COVERAGE_HAMMER_ON = parts[1].strip().lower() == "on"
                ok(f"Self-study continuation hammer: {COVERAGE_HAMMER_ON}")
            else:
                err("Usage: /book.hammer on|off")

        elif cmd == "/out.budget":
            if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                OUTPUT_BUDGET_SNIPPET_ON = parts[1].strip().lower() == "on"
                ok(f"OUTPUT_BUDGET addendum: {OUTPUT_BUDGET_SNIPPET_ON}")
            else:
                err("Usage: /out.budget on|off")

        elif cmd == "/out.push":
            if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                OUTPUT_PUSH_ON = parts[1].strip().lower() == "on"
                ok(f"Output push: {OUTPUT_PUSH_ON}")
            else:
                err("Usage: /out.push on|off")

        elif cmd == "/out.minchars":
            if len(parts) >= 2:
                try:
                    v = int(parts[1])
                    if v < 1000:
                        warn("Value too small; suggest >= 2500.")
                    OUTPUT_MIN_CHARS = max(1000, v)
                    ok(f"OUTPUT_MIN_CHARS={OUTPUT_MIN_CHARS}")
                except:
                    err("Provide an integer.")
            else:
                err("Usage: /out.minchars <N>")

        elif cmd == "/out.passes":
            if len(parts) >= 2:
                try:
                    v = int(parts[1])
                    if v < 0 or v > 10:
                        warn("Unusual value; using within [0..10].")
                    OUTPUT_PUSH_MAX_PASSES = max(0, min(10, v))
                    ok(f"OUTPUT_PUSH_MAX_PASSES={OUTPUT_PUSH_MAX_PASSES}")
                except:
                    err("Provide an integer.")
            else:
                err("Usage: /out.passes <N>")

        elif cmd == "/next":
            if len(parts) >= 2:
                hint = " ".join(parts[1:])
                NEXT_OVERRIDE = hint
                ok(f"Next override set: {hint}")
            else:
                err("Usage: /next <hint>")

        elif cmd == "/window":
            if len(parts) >= 2 and parts[1].isdigit():
                n = int(parts[1])
                if n < 1:
                    err("Window must be >= 1")
                else:
                    HISTORY_WINDOW = n
                    ok(f"History window: {HISTORY_WINDOW}")
            else:
                err("Usage: /window <N>")

        elif cmd == "/model":
            if len(parts) >= 2:
                MODEL_ID = parts[1]
                ok(f"Model set: {MODEL_ID}")
            else:
                err("Usage: /model <model_id>")

        elif cmd == "/system.set":
            if len(parts) >= 2:
                SYSTEM_PROMPT = " ".join(parts[1:])
                ok("System prompt updated.")
            else:
                err("Usage: /system.set <prompt>")

        elif cmd == "/system.clear":
            SYSTEM_PROMPT = ""
            ok("System prompt cleared.")

        elif cmd == "/system":
            SYSTEM_PROMPT = parts[1] if len(parts) >= 2 else ""
            ok("System set." if SYSTEM_PROMPT else "System cleared.")
        elif cmd == "/systemfile" and len(parts) >= 2:
            try:
                with open(parts[1], "r", encoding="utf-8") as f:
                    SYSTEM_PROMPT = f.read()
                ok(f"Loaded system from {parts[1]}")
            except Exception as e:
                err(f"Failed: {e}")
        elif cmd == "/system.append":
            add = await read_multiline()
            if add.strip():
                SYSTEM_PROMPT = (
                    SYSTEM_PROMPT + ("\n\n" if SYSTEM_PROMPT.strip() else "") + add
                ).strip()
                ok("System appended.")
            else:
                warn("Nothing pasted.")

        elif cmd == "/repeat.warn":
            if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                REPEAT_WARN = parts[1].strip().lower() == "on"
                ok(f"Repeat warn: {REPEAT_WARN}")
            else:
                err("Usage: /repeat.warn on|off")

        elif cmd == "/repeat.thresh":
            if len(parts) >= 2:
                try:
                    t = float(parts[1])
                    if t <= 0 or t >= 1:
                        warn("Use a value between 0 and 1 (e.g., 0.35).")
                    else:
                        REPEAT_THRESH = t
                        ok(f"Repeat threshold: {REPEAT_THRESH}")
                except:
                    err("Provide a float (0..1).")
            else:
                err("Usage: /repeat.thresh <0..1>")

        elif cmd == "/debug.cont":
            anch = continuation_anchor(CONT_ANCHOR_CHARS)
            print(hr())
            print(f"Anchor ({len(anch)} chars): {anch!r}")
            print(f"LAST_NEXT_HINT: {LAST_NEXT_HINT!r}")
            print(hr())

        elif cmd == "/debug.ctx":
            ctx = trimmed_history()
            print(hr())
            print(f"Context messages included: {len(ctx)}")
            if ctx:
                print(
                    f"First in ctx: {ctx[0]['role']} … Last in ctx: {ctx[-1]['role']}"
                )
            print(hr())

        # Cloudflare commands
        elif cmd == "/cf.status":
            print(hr())
            print(f"CF_BLOCKED={CF_BLOCKED}  CF_NOTIFIED={CF_NOTIFIED}")
            print(f"Autopilot paused={AUTO_PAUSE}")
            print(hr())

        elif cmd == "/cf.resume":
            # You call this after solving CF in the browser.
            CF_BLOCKED = False
            CF_NOTIFIED = False
            ok(
                "Cloudflare cleared. Now run /book.resume to continue generation (or keep it paused to /next steer)."
            )

        elif cmd == "/cf.reset":
            # hard reset flags; won't auto-resume
            CF_BLOCKED = False
            CF_NOTIFIED = False
            ok("CF flags reset.")

        # OpenRouter commands
        elif cmd == "/backend":
            if len(parts) >= 2 and parts[1].strip().lower() in (
                "bridge",
                "openrouter",
            ):
                BE = parts[1].strip().lower()
                BACKEND = BE
                ok(f"Backend: {BACKEND}")
            else:
                err("Usage: /backend bridge|openrouter")

        elif cmd == "/or.model":
            if len(parts) >= 2:
                OR_MODEL = parts[1].strip()
                ok(f"OpenRouter model set: {OR_MODEL}")
            else:
                err("Usage: /or.model <model-id>")

        elif cmd == "/or.ref":
            if len(parts) >= 2:
                OR_REFERRER = parts[1].strip()
                ok(f"OpenRouter Referer set: {OR_REFERRER}")
                _or_init(force=True)
            else:
                err("Usage: /or.ref <url>")

        elif cmd == "/or.title":
            if len(parts) >= 2:
                OR_TITLE = parts[1].strip()
                ok(f"OpenRouter Title set: {OR_TITLE}")
                _or_init(force=True)
            else:
                err("Usage: /or.title <text>")

        elif cmd == "/or.status":
            print(hr())
            print(f"Backend: {BACKEND}")
            print(f"OR_BASE_URL: {OR_BASE_URL}")
            print(f"OR_MODEL: {OR_MODEL or '(openrouter/auto)'}")
            print(f"OR_API_KEY set: {'yes' if OR_API_KEY else 'no'}")
            print(f"OR_HEADERS: {OR_HEADERS or '{}'}")
            print(hr())

        # Ingestion/Synthesis/Lossless/Style
        elif cmd == "/ingest.ack" and len(parts) >= 2:
            path = parts[1]
            chunk_kb = 80
            if len(parts) == 3:
                try:
                    chunk_kb = max(8, int(parts[2]))
                except:
                    pass
            if ING_TASK and not ING_TASK.done():
                warn("Ingestion already running.")
                prompt()
                return
            ING_TASK = asyncio.create_task(ingest_ack_loop(path, chunk_kb))
            ok(f"Started ACK ingestion from {path}")
        elif cmd == "/ingest.synth":
            toks = line.split()
            if len(toks) < 3:
                err(
                    "Usage: /ingest.synth <file> <synth.md> [chunkKB=45] [synthChars=9500]"
                )
            else:
                path = toks[1]
                out = toks[2]
                chunk_kb = int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 45
                synth_chars = (
                    int(toks[4]) if len(toks) >= 5 and toks[4].isdigit() else 9500
                )
                if ING_TASK and not ING_TASK.done():
                    warn("Ingestion already running.")
                    prompt()
                    return
                ING_TASK = asyncio.create_task(
                    ingest_synth_loop(path, out, chunk_kb, synth_chars)
                )
                ok(f"Started SYNTH ingestion from {path} → {out}")
        elif cmd == "/ingest.lossless":
            toks = line.split()
            if len(toks) < 3:
                err(
                    "Usage: /ingest.lossless <file> <synth.md> [chunkKB=45] [synthChars=12000]"
                )
            else:
                path = toks[1]
                out = toks[2]
                chunk_kb = int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 45
                synth_chars = (
                    int(toks[4]) if len(toks) >= 5 and toks[4].isdigit() else 12000
                )
                if ING_TASK and not ING_TASK.done():
                    warn("Ingestion already running.")
                    prompt()
                    return
                ING_TASK = asyncio.create_task(
                    ingest_synth_loop(path, out, chunk_kb, synth_chars)
                )
                ok(f"Started LOSSLESS synthesis from {path} → {out}")
        elif cmd == "/ingest.stop":
            if ING_ON:
                ING_ON = False
                ok("Stopping ingestion…")
            else:
                warn("No ingestion running.")
        elif cmd == "/ingest.status":
            show_status()
        elif cmd == "/style.capture":
            toks = line.split()
            if len(toks) < 3:
                err(
                    "Usage: /style.capture <file> <style.synth.md> [chunkKB=30] [styleChars=6000]"
                )
                prompt()
                return
            path, out = toks[1], toks[2]
            chunk_kb = int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 30
            style_chars = int(toks[4]) if len(toks) >= 5 and toks[4].isdigit() else 6000
            if ING_TASK and not ING_TASK.done():
                warn("Ingestion already running.")
                prompt()
                return
            ING_TASK = asyncio.create_task(
                ingest_style_loop(path, out, chunk_kb, style_chars)
            )
            ok(f"Started style capture from {path} → {out}")
        elif cmd == "/style.apply":
            toks = line.split()
            if len(toks) < 3:
                err(
                    "Usage: /style.apply <style.synth.md> <topic|file> [out.md] [--words=N]"
                )
                prompt()
                return
            style, topic = toks[1], toks[2]
            out = None
            words = None
            for tk in toks[3:]:
                if tk.startswith("--words="):
                    try:
                        words = int(tk.split("=", 1)[1])
                    except:
                        pass
                else:
                    out = tk
            await style_apply(
                style, topic, out, words=None if not words else int(words)
            )

        # Rewrite/Lossless
        elif cmd == "/rewrite.start":
            toks = line.split()
            if len(toks) < 3:
                err("Usage: /rewrite.start <synth.md> <out.md>")
            else:
                await rewrite_start(toks[1], toks[2])
        elif cmd == "/rewrite.lossless":
            toks = line.split()
            if len(toks) < 2:
                err("Usage: /rewrite.lossless <synth.md> [out.md]")
            else:
                synth = toks[1]
                out = toks[2] if len(toks) >= 3 else None
                await rewrite_lossless(synth, out)

        # One-shot lossless pipeline
        elif cmd == "/lossless.run":
            toks = line.split()
            if len(toks) < 2:
                err(
                    "Usage: /lossless.run <file> [--outdir=DIR] [--chunkKB=45] [--synthChars=12000]"
                )
                prompt()
                return
            path = toks[1]
            outdir = None
            ck = 45
            sc = 12000
            for tk in toks[2:]:
                if tk.startswith("--outdir="):
                    outdir = tk.split("=", 1)[1]
                elif tk.startswith("--chunkKB="):
                    try:
                        ck = int(tk.split("=", 1)[1])
                    except:
                        pass
                elif tk.startswith("--synthChars="):
                    try:
                        sc = int(tk.split("=", 1)[1])
                    except:
                        pass
            await lossless_run(path, outdir, chunk_kb=ck, synth_chars=sc)

        # NEW: Bilingual and Policy commands
        elif cmd == "/bilingual.file":
            # /bilingual.file <file> --lang=LANG [--outdir=DIR] [--chunkKB=45]
            toks = line.split()
            if len(toks) < 2:
                err(
                    "Usage: /bilingual.file <file> --lang=LANG [--outdir=DIR] [--chunkKB=45]"
                )
            else:
                path = toks[1]
                lang = None
                outdir = None
                ck = 45
                for tk in toks[2:]:
                    if tk.startswith("--lang="):
                        lang = tk.split("=", 1)[1]
                    elif tk.startswith("--outdir="):
                        outdir = tk.split("=", 1)[1]
                    elif tk.startswith("--chunkKB="):
                        ck = int(tk.split("=", 1)[1])
                if not lang:
                    err("Provide --lang=LANG")
                else:
                    await bilingual_transform_file(path, lang, outdir, chunk_kb=ck)

        elif cmd == "/policy.from":
            # /policy.from <reg_file> <out_dir> [--org="..."] [--jurisdiction="..."] [--chunkKB=45] [--synthChars=16000]
            toks = line.split()
            if len(toks) < 3:
                err(
                    'Usage: /policy.from <reg_file> <out_dir> [--org="..."] [--jurisdiction="..."] [--chunkKB=45] [--synthChars=16000]'
                )
            else:
                reg = toks[1]
                outd = toks[2]
                org = None
                juris = None
                ck = 45
                sc = 16000
                for tk in toks[3:]:
                    if tk.startswith("--org="):
                        org = tk.split("=", 1)[1].strip('"')
                    elif tk.startswith("--jurisdiction="):
                        juris = tk.split("=", 1)[1].strip('"')
                    elif tk.startswith("--chunkKB="):
                        ck = int(tk.split("=", 1)[1])
                    elif tk.startswith("--synthChars="):
                        sc = int(tk.split("=", 1)[1])
                await policy_from_regulations(
                    reg,
                    outd,
                    org=org,
                    jurisdiction=juris,
                    chunk_kb=ck,
                    synth_chars=sc,
                )

        # Study/Translate
        elif cmd == "/flashcards.from":
            toks = line.split()
            if len(toks) < 3:
                err("Usage: /flashcards.from <synth.md> <out.md> [n=200]")
                prompt()
                return
            n = int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 200
            await flashcards_from_synth(toks[1], toks[2], n=n)
        elif cmd == "/glossary.from":
            toks = line.split()
            if len(toks) < 3:
                err("Usage: /glossary.from <synth.md> <out.md>")
                prompt()
                return
            await glossary_from_synth(toks[1], toks[2])
        elif cmd == "/index.from":
            toks = line.split()
            if len(toks) < 3:
                err("Usage: /index.from <synth.md> <out.md>")
                prompt()
                return
            await index_from_synth(toks[1], toks[2])
        elif cmd == "/translate.file":
            toks = line.split()
            if len(toks) < 3:
                err("Usage: /translate.file <file> <language> [chunkKB=50]")
                prompt()
                return
            chunk_kb = int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 50
            await translate_file(toks[1], " ".join(toks[2:3]), chunk_kb=chunk_kb)
        elif cmd == "/chad":
            # /chad "What is X?" [--depth=short|medium|deep] [--prose] [--norefs] [--nocontra]
            m = re.findall(r'"([^"]+)"', line)
            if not m:
                err(
                    'Usage: /chad "your question" [--depth=short|medium|deep] [--prose] [--norefs] [--nocontra]'
                )
                prompt()
                return
            q = m[0]
            depth = "short"
            bullets = True
            refs = True
            contra = True
            for tk in line.split():
                if tk.startswith("--depth="):
                    depth = tk.split("=", 1)[1].strip().lower()
                elif tk == "--prose":
                    bullets = False
                elif tk == "--norefs":
                    refs = False
                elif tk == "--nocontra":
                    contra = False
            await answer_chad(q, depth=depth, bullets=bullets, refs=refs, contra=contra)
            prompt()
            return

        # Snapshot
        elif cmd == "/snapshot":
            # optional flag: --chunk
            do_chunk = "--chunk" in line or "-c" in line
            args = ["bash", "snapshot.sh"]
            if do_chunk:
                args.append("--chunk")
            try:
                subprocess.run(args, check=False)
                ok("Snapshot command executed.")
            except Exception as e:
                err(f"Snapshot failed: {e}")

        # Prompt Booster commands
        elif cmd == "/prompt.boost":
            # /prompt.boost "goal" [--ask] [--apply] [--meta]
            m = re.findall(r'"([^"]+)"', line)
            if not m:
                err('Usage: /prompt.boost "your goal" [--ask] [--apply] [--meta]')
                prompt()
                return
            goal = m[0]
            ask = "--ask" in line
            meta = "--meta" in line
            pr = await prompt_boost(goal, ask=ask or True, meta=meta)
            if ("--apply" in line) and BOOST_LAST_PROMPT:
                prompt_apply("next")

        elif cmd == "/prompt.answer":
            # multiline answers
            ans = await read_multiline(
                "Paste answers (number or bullet wise). End with: EOF"
            )
            if ans.strip():
                await prompt_answer(ans)
            else:
                warn("No answers provided.")

        elif cmd == "/prompt.apply":
            where = "next"
            if len(parts) >= 2 and parts[1].strip().lower() in ("next", "system"):
                where = parts[1].strip().lower()
            prompt_apply(where)

        # Recipe runner commands
        elif cmd == "/run.recipe":
            toks = line.split()
            if len(toks) < 2:
                err("Usage: /run.recipe <recipe.(json|yml|yaml)>")
                prompt()
                return
            await run_recipe_file(toks[1])

        elif cmd == "/run.quick":
            # fast inline recipe: /run.quick task=book.zero2hero subject="X" out=./books/x.md max=6 style=no-bs,chad
            args = {}
            for tk in line.split()[1:]:
                if "=" in tk:
                    k, v = tk.split("=", 1)
                    args[k] = v.strip('"')
            rec = {
                "task": args.get("task", "book.zero2hero"),
                "subject": args.get("subject"),
                "styles": (
                    (args.get("style", "") or args.get("styles", "")).split(",")
                    if args.get("style") or args.get("styles")
                    else []
                ),
                "io": {"output": "file", "outPath": args.get("out")},
                "max_chunks": (
                    int(args["max"])
                    if args.get("max") and args["max"].isdigit()
                    else None
                ),
            }
            await run_recipe(rec)

        # Project/Pipeline
        elif cmd == "/project.init":
            # /project.init [--dir=.]
            dir_path = "."
            for tk in line.split()[1:]:
                if tk.startswith("--dir="):
                    dir_path = tk.split("=", 1)[1]

            root_dir = os.path.abspath(dir_path)
            lmastudio_dir = os.path.join(root_dir, ".lmastudio")

            ensure_dir(lmastudio_dir)
            ensure_dir(os.path.join(lmastudio_dir, "checkpoints"))
            ensure_dir(os.path.join(lmastudio_dir, "refs"))
            ensure_dir(os.path.join(root_dir, "pipelines"))
            ensure_dir(os.path.join(root_dir, "recipes"))
            ensure_dir(os.path.join(root_dir, "workspace"))
            ensure_dir(os.path.join(root_dir, "outputs"))
            ensure_dir(os.path.join(root_dir, "books"))

            # Create project.yml placeholder
            proj_yml_path = os.path.join(lmastudio_dir, "project.yml")
            if not os.path.exists(proj_yml_path):
                with open(proj_yml_path, "w", encoding="utf-8") as f:
                    f.write("default_backend: bridge\n")
                    f.write("default_model: null\n")
                    f.write("paths:\n")
                    f.write("  workspace: workspace/\n")
                    f.write("  outputs: outputs/\n")

            ok(f"Project scaffold created in: {root_dir}")

        elif cmd == "/pipeline.run":
            toks = line.split()
            if len(toks) < 2:
                err("Usage: /pipeline.run <pipeline.yml>")
                prompt()
                return
            if not PipelineExecutor:
                err("PipelineExecutor not available. Check imports and dependencies.")
                prompt()
                return

            # Pass self (the current module/context) to the executor for callbacks
            executor = PipelineExecutor(sys.modules[__name__], ok, warn, err)
            await executor.execute_pipeline(toks[1])

        # Checkpoint commands
        elif cmd == "/book.save":
            # /book.save [name]
            name = parts[1] if len(parts) >= 2 else None
            await book_save(name)

        elif cmd == "/book.load":
            # /book.load <name>
            if len(parts) < 2:
                err("Usage: /book.load <name>")
                prompt()
                return
            await book_load(parts[1])

        # Macro commands
        elif cmd == "/macro.save":
            # /macro.save <name> <command template>
            toks = line.split(maxsplit=2)
            if len(toks) < 3:
                err('Usage: /macro.save <name> "<command template>"')
                prompt()
                return
            name = toks[1]
            template = toks[2].strip().strip('"')
            MACROS[name] = template
            _save_macros()
            ok(f"Macro '{name}' saved.")

        elif cmd == "/macro.list":
            if not MACROS:
                warn("No macros defined.")
                prompt()
                return
            print(hr())
            print("Macros:")
            for name, template in MACROS.items():
                print(f"  {name}: {template}")
            print(hr())

        elif cmd == "/macro.delete":
            if len(parts) < 2:
                err("Usage: /macro.delete <name>")
                prompt()
                return
            name = parts[1]
            if name in MACROS:
                del MACROS[name]
                _save_macros()
                ok(f"Macro '{name}' deleted.")
            else:
                warn(f"Macro '{name}' not found.")

        elif cmd == "/macro.run":
            # /macro.run <name> [arg1 arg2 ...]
            toks = line.split()
            if len(toks) < 2:
                err("Usage: /macro.run <name> [args...]")
                prompt()
                return
            name = toks[1]
            args = toks[2:]

            command = _run_macro(name, args)
            if command:
                ok(f"Running macro: {command}")
                # Recursively call _handle_command with the expanded command
                await _handle_command(command)

        # Manual autopilot
        elif cmd == "/book.start" and len(parts) >= 2:
            AUTO_OUT = parts[1]
            AUTO_ON = True
            AUTO_COUNT = 0
            LAST_NEXT_HINT = None
            ok(f"Autopilot ON → {AUTO_OUT}")
            if AUTO_TASK and not AUTO_TASK.done():
                AUTO_TASK.cancel()
            AUTO_TASK = asyncio.create_task(autorun_loop())
        elif cmd == "/book.stop":
            AUTO_ON = False
            ok("Autopilot OFF.")
        elif cmd == "/book.max" and len(parts) >= 2:
            try:
                n = int(parts[1])
                AUTO_MAX = None if n <= 0 else n
                ok(f"Auto max={AUTO_MAX or '(unlimited)'}")
            except:
                err("Provide an integer.")
        elif cmd == "/book.status":
            show_status()

        # Misc
        elif cmd == "/mono":
            global USE_COLOR
            USE_COLOR = not USE_COLOR
            _apply_colors()
            ok(f"Monochrome {'ON' if not USE_COLOR else 'OFF'}.")
        elif cmd == "/image":
            if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                global IMAGE_MARKDOWN
                IMAGE_MARKDOWN = parts[1].strip().lower() == "on"
                ok(f"Images → {IMAGE_MARKDOWN}")
            else:
                err("Usage: /image on|off")
        elif cmd == "/clear":
            HISTORY.clear()
            ok("History cleared.")
        elif cmd == "/history.tail":
            try:
                u = next((m for m in reversed(HISTORY) if m["role"] == "user"), None)
                a = next(
                    (m for m in reversed(HISTORY) if m["role"] == "assistant"), None
                )
                print(hr())
                if u:
                    print(
                        f"Last user: {u['content'][:500] + ('...' if len(u['content'])>500 else '')}"
                    )
                if a:
                    print(
                        f"Last assistant: {a['content'][:500] + ('...' if len(a['content'])>500 else '')}"
                    )
                print(hr())
            except Exception as e:
                err(f"history.tail failed: {e}")
        else:
            warn("Unknown command. /help for help.")
        return

    # manual chat
    if AUTO_ON:
        warn(
            "Autopilot running. Use /book.pause and /next to intervene, or /book.stop to stop."
        )
        return
    try:
        await ask_collect(line)
    except Exception as e:
        err(f"Error: {e}")


async def repl():
    global CAPTURE_FLAG, SESSION_ID, MESSAGE_ID, SYSTEM_PROMPT, MODEL_ID
    global AUTO_ON, AUTO_TASK, AUTO_OUT, AUTO_MAX, AUTO_COUNT, LAST_NEXT_HINT, NEXT_OVERRIDE, AUTO_PAUSE
    global ING_ON, ING_TASK, ING_MODE, ING_PATH, ING_POS, ING_TOTAL, ING_CHUNK_BYTES, SYNTH_LIMIT, SYNTH_OUT
    global BACKEND, OR_MODEL, OR_REFERRER, OR_TITLE

    help_text()
    prompt()
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        line = line.rstrip("\n")
        if not line.strip():
            prompt()
            continue

        if line.startswith("/"):
            parts = line.split(" ", 2)
            cmd = parts[0].lower()

            # Core
            if cmd == "/help":
                help_text()
            elif cmd == "/exit":
                print("Bye.")
                raise SystemExit(0)
            elif cmd == "/status":
                show_status()
            elif cmd == "/capture":
                CAPTURE_FLAG = True
                ok("Capture ON. Click Retry in LMArena.")
            elif cmd == "/setids" and len(parts) >= 3:
                SESSION_ID, MESSAGE_ID = parts[1], parts[2]
                ok("IDs set.")
            elif cmd == "/showids":
                print(
                    f"session_id={SESSION_ID or '(unset)'}\nmessage_id={MESSAGE_ID or '(unset)'}"
                )

            # Repo
            elif cmd == "/repo.list":
                print(repo_list())
            elif cmd == "/repo.show":
                toks = line.split()
                if len(toks) < 2:
                    err("Usage: /repo.show <key> [n]")
                else:
                    key = toks[1]
                    if key not in PROMPT_REPO:
                        err("Unknown key.")
                    else:
                        n = (
                            int(toks[2])
                            if len(toks) >= 3 and toks[2].isdigit()
                            else 500
                        )
                        text = PROMPT_REPO[key]["system"]
                        print((text[:n] + ("..." if len(text) > n else "")))
            elif cmd == "/repo.use":
                toks = line.split()
                if len(toks) < 2:
                    err("Usage: /repo.use <key> [args]")
                    prompt()
                    continue
                key = toks[1]
                if key not in PROMPT_REPO:
                    err("Unknown repo key.")
                    prompt()
                    continue
                if key == "translate":
                    if len(toks) < 3:
                        err("Usage: /repo.use translate <lang>")
                        prompt()
                        continue
                    set_system(repo_render("translate", lang=" ".join(toks[2:])))
                    ok("Translator system set.")
                elif key == "brainstorm":
                    set_system(repo_render("brainstorm"))
                    ok("Brainstorm system set.")
                elif key in (
                    "book.zero2hero",
                    "book.reference",
                    "book.pop",
                    "exam.cram",
                    "book.bilingual",
                ):
                    if len(toks) < 3:
                        err(f"Usage: /repo.use {key} <subject>")
                        prompt()
                        continue
                    if key == "book.bilingual":
                        # Special case for bilingual - needs lang
                        subject = toks[2]
                        lang = None
                        for tk in toks[3:]:
                            if tk.startswith("--lang="):
                                lang = tk.split("=", 1)[1]
                                break
                        if not lang:
                            err("For /repo.use book.bilingual, provide --lang=LANG")
                            prompt()
                            continue
                        set_system(repo_render(key, subject=subject, lang=lang))
                    else:
                        set_system(repo_render(key, subject=" ".join(toks[2:])))
                    ok(f"{key} system set.")
                elif key == "book.lossless.rewrite":
                    set_system(PROMPT_REPO[key]["system"])
                    ok("Lossless rewrite system set.")
                else:
                    set_system(PROMPT_REPO[key]["system"])
                    ok(f"{key} system set.")

            # Subject-aware book modes
            elif cmd == "/book.zero2hero":
                if len(parts) < 2:
                    err(
                        "Usage: /book.zero2hero <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"
                    )
                    prompt()
                    continue
                tokens = line.split()[1:]
                subject_tokens = []
                plan = False
                maxc = None
                wind = None
                outdir = None
                for tk in tokens:
                    if tk == "--plan":
                        plan = True
                    elif tk.startswith("--max="):
                        try:
                            maxc = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--window="):
                        try:
                            wind = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--outdir="):
                        outdir = tk.split("=", 1)[1]
                    elif tk.startswith("--"):
                        pass
                    else:
                        subject_tokens.append(tk)
                if not subject_tokens:
                    err("Provide a subject, e.g., /book.zero2hero Psychology")
                    prompt()
                    continue
                await book_zero2hero(" ".join(subject_tokens), plan, outdir, maxc, wind)

            elif cmd == "/book.reference":
                if len(parts) < 2:
                    err(
                        "Usage: /book.reference <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"
                    )
                    prompt()
                    continue
                tokens = line.split()[1:]
                subject_tokens = []
                plan = False
                maxc = None
                wind = None
                outdir = None
                for tk in tokens:
                    if tk == "--plan":
                        plan = True
                    elif tk.startswith("--max="):
                        try:
                            maxc = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--window="):
                        try:
                            wind = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--outdir="):
                        outdir = tk.split("=", 1)[1]
                    elif tk.startswith("--"):
                        pass
                    else:
                        subject_tokens.append(tk)
                if not subject_tokens:
                    err("Provide a subject.")
                    prompt()
                    continue
                await book_reference(" ".join(subject_tokens), plan, outdir, maxc, wind)

            elif cmd == "/book.pop":
                if len(parts) < 2:
                    err(
                        "Usage: /book.pop <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"
                    )
                    prompt()
                    continue
                tokens = line.split()[1:]
                subject_tokens = []
                plan = False
                maxc = None
                wind = None
                outdir = None
                for tk in tokens:
                    if tk == "--plan":
                        plan = True
                    elif tk.startswith("--max="):
                        try:
                            maxc = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--window="):
                        try:
                            wind = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--outdir="):
                        outdir = tk.split("=", 1)[1]
                    elif tk.startswith("--"):
                        pass
                    else:
                        subject_tokens.append(tk)
                if not subject_tokens:
                    err("Provide a subject.")
                    prompt()
                    continue
                await book_pop(" ".join(subject_tokens), plan, outdir, maxc, wind)

            elif cmd == "/book.nobs":
                if len(parts) < 2:
                    err(
                        "Usage: /book.nobs <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"
                    )
                    prompt()
                    continue
                tokens = line.split()[1:]
                subject_tokens = []
                plan = False
                maxc = None
                wind = None
                outdir = None
                for tk in tokens:
                    if tk == "--plan":
                        plan = True
                    elif tk.startswith("--max="):
                        try:
                            maxc = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--window="):
                        try:
                            wind = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--outdir="):
                        outdir = tk.split("=", 1)[1]
                    elif tk.startswith("--"):
                        pass
                    else:
                        subject_tokens.append(tk)
                if not subject_tokens:
                    err("Provide a subject.")
                    prompt()
                    continue
                await book_nobs(" ".join(subject_tokens), plan, outdir, maxc, wind)

            elif cmd == "/book.bilingual":
                # /book.bilingual <subject> --lang=LANG [--plan] [--max=N] [--window=N] [--outdir=DIR]
                tokens = line.split()[1:]
                subject_tokens = []
                plan = False
                maxc = None
                wind = None
                outdir = None
                lang = None
                for tk in tokens:
                    if tk == "--plan":
                        plan = True
                    elif tk.startswith("--lang="):
                        lang = tk.split("=", 1)[1]
                    elif tk.startswith("--max="):
                        maxc = int(tk.split("=", 1)[1])
                    elif tk.startswith("--window="):
                        wind = int(tk.split("=", 1)[1])
                    elif tk.startswith("--outdir="):
                        outdir = tk.split("=", 1)[1]
                    elif tk.startswith("--"):
                        pass
                    else:
                        subject_tokens.append(tk)
                if not subject_tokens or not lang:
                    err(
                        "Usage: /book.bilingual <subject> --lang=LANG [--plan] [--max=N] [--window=N] [--outdir=DIR]"
                    )
                else:
                    await book_bilingual(
                        " ".join(subject_tokens), lang, plan, outdir, maxc, wind
                    )

            elif cmd == "/exam.cram":
                if len(parts) < 2:
                    err(
                        "Usage: /exam.cram <subject> [--max=N] [--window=N] [--outdir=DIR]"
                    )
                    prompt()
                    continue
                tokens = line.split()[1:]
                subject_tokens = []
                maxc = None
                wind = None
                outdir = None
                for tk in tokens:
                    if tk.startswith("--max="):
                        try:
                            maxc = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--window="):
                        try:
                            wind = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--outdir="):
                        outdir = tk.split("=", 1)[1]
                    elif tk.startswith("--"):
                        pass
                    else:
                        subject_tokens.append(tk)
                if not subject_tokens:
                    err("Provide a subject.")
                    prompt()
                    continue
                await exam_cram(" ".join(subject_tokens), outdir, maxc, wind)

            # Autopilot control
            elif cmd == "/book.pause":
                AUTO_PAUSE = True
                ok(
                    "Autopilot paused. Use /book.resume or /next to override next prompt."
                )
            elif cmd == "/book.resume":
                AUTO_PAUSE = False
                ok("Autopilot resumed.")
            elif cmd == "/next":
                if len(parts) < 2:
                    err(
                        "Usage: /next <text>. Example: /next Continue up to master's level; do not end after basics."
                    )
                else:
                    NEXT_OVERRIDE = parts[1]
                    ok(f"Next prompt override set: {NEXT_OVERRIDE!r}")

            elif cmd == "/book.hammer":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                    COVERAGE_HAMMER_ON = parts[1].strip().lower() == "on"
                    ok(f"Self-study continuation hammer: {COVERAGE_HAMMER_ON}")
                else:
                    err("Usage: /book.hammer on|off")

            elif cmd == "/out.budget":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                    OUTPUT_BUDGET_SNIPPET_ON = parts[1].strip().lower() == "on"
                    ok(f"OUTPUT_BUDGET addendum: {OUTPUT_BUDGET_SNIPPET_ON}")
                else:
                    err("Usage: /out.budget on|off")

            elif cmd == "/out.push":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                    OUTPUT_PUSH_ON = parts[1].strip().lower() == "on"
                    ok(f"Output push: {OUTPUT_PUSH_ON}")
                else:
                    err("Usage: /out.push on|off")

            elif cmd == "/out.minchars":
                if len(parts) >= 2:
                    try:
                        v = int(parts[1])
                        if v < 1000:
                            warn("Value too small; suggest >= 2500.")
                        OUTPUT_MIN_CHARS = max(1000, v)
                        ok(f"OUTPUT_MIN_CHARS={OUTPUT_MIN_CHARS}")
                    except:
                        err("Provide an integer.")
                else:
                    err("Usage: /out.minchars <N>")

            elif cmd == "/out.passes":
                if len(parts) >= 2:
                    try:
                        v = int(parts[1])
                        if v < 0 or v > 10:
                            warn("Unusual value; using within [0..10].")
                        OUTPUT_PUSH_MAX_PASSES = max(0, min(10, v))
                        ok(f"OUTPUT_PUSH_MAX_PASSES={OUTPUT_PUSH_MAX_PASSES}")
                    except:
                        err("Provide an integer.")
                else:
                    err("Usage: /out.passes <N>")

            # Cloudflare commands
            elif cmd == "/cf.status":
                print(hr())
                print(f"CF_BLOCKED={CF_BLOCKED}  CF_NOTIFIED={CF_NOTIFIED}")
                print(f"Autopilot paused={AUTO_PAUSE}")
                print(hr())

            elif cmd == "/cf.resume":
                # You call this after solving CF in the browser.
                CF_BLOCKED = False
                CF_NOTIFIED = False
                ok(
                    "Cloudflare cleared. Now run /book.resume to continue generation (or keep it paused to /next steer)."
                )

            elif cmd == "/cf.reset":
                # hard reset flags; won't auto-resume
                CF_BLOCKED = False
                CF_NOTIFIED = False
                ok("CF flags reset.")

            # Prompt & Model
            elif cmd == "/system":
                SYSTEM_PROMPT = parts[1] if len(parts) >= 2 else ""
                ok("System set." if SYSTEM_PROMPT else "System cleared.")
            elif cmd == "/systemfile" and len(parts) >= 2:
                try:
                    with open(parts[1], "r", encoding="utf-8") as f:
                        SYSTEM_PROMPT = f.read()
                    ok(f"Loaded system from {parts[1]}")
                except Exception as e:
                    err(f"Failed: {e}")
            elif cmd == "/system.append":
                add = await read_multiline()
                if add.strip():
                    SYSTEM_PROMPT = (
                        SYSTEM_PROMPT + ("\n\n" if SYSTEM_PROMPT.strip() else "") + add
                    ).strip()
                    ok("System appended.")
                else:
                    warn("Nothing pasted.")
            elif cmd == "/model":
                if len(parts) >= 2:
                    arg = parts[1].strip().lower()
                    if arg == "none":
                        MODEL_ID = None
                        ok("Model cleared.")
                    else:
                        MODEL_ID = parts[1].strip()
                        ok(f"Model={MODEL_ID}")
                else:
                    print(f"Current model: {MODEL_ID or '(session default)'}")
            elif cmd == "/window" and len(parts) >= 2:
                try:
                    set_window(int(parts[1]))
                    ok(f"Window={HISTORY_WINDOW}")
                except:
                    err("Provide an integer.")

            # OpenRouter commands
            elif cmd == "/backend":
                if len(parts) >= 2 and parts[1].strip().lower() in (
                    "bridge",
                    "openrouter",
                ):
                    BE = parts[1].strip().lower()
                    BACKEND = BE
                    ok(f"Backend: {BACKEND}")
                else:
                    err("Usage: /backend bridge|openrouter")

            elif cmd == "/or.model":
                if len(parts) >= 2:
                    OR_MODEL = parts[1].strip()
                    ok(f"OpenRouter model set: {OR_MODEL}")
                else:
                    err("Usage: /or.model <model-id>")

            elif cmd == "/or.ref":
                if len(parts) >= 2:
                    OR_REFERRER = parts[1].strip()
                    ok(f"OpenRouter Referer set: {OR_REFERRER}")
                    _or_init(force=True)
                else:
                    err("Usage: /or.ref <url>")

            elif cmd == "/or.title":
                if len(parts) >= 2:
                    OR_TITLE = parts[1].strip()
                    ok(f"OpenRouter Title set: {OR_TITLE}")
                    _or_init(force=True)
                else:
                    err("Usage: /or.title <text>")

            elif cmd == "/or.status":
                print(hr())
                print(f"Backend: {BACKEND}")
                print(f"OR_BASE_URL: {OR_BASE_URL}")
                print(f"OR_MODEL: {OR_MODEL or '(openrouter/auto)'}")
                print(f"OR_API_KEY set: {'yes' if OR_API_KEY else 'no'}")
                print(f"OR_HEADERS: {OR_HEADERS or '{}'}")
                print(hr())

            # Ingestion/Synthesis/Lossless/Style
            elif cmd == "/ingest.ack" and len(parts) >= 2:
                path = parts[1]
                chunk_kb = 80
                if len(parts) == 3:
                    try:
                        chunk_kb = max(8, int(parts[2]))
                    except:
                        pass
                if ING_TASK and not ING_TASK.done():
                    warn("Ingestion already running.")
                    prompt()
                    continue
                ING_TASK = asyncio.create_task(ingest_ack_loop(path, chunk_kb))
                ok(f"Started ACK ingestion from {path}")
            elif cmd == "/ingest.synth":
                toks = line.split()
                if len(toks) < 3:
                    err(
                        "Usage: /ingest.synth <file> <synth.md> [chunkKB=45] [synthChars=9500]"
                    )
                else:
                    path = toks[1]
                    out = toks[2]
                    chunk_kb = (
                        int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 45
                    )
                    synth_chars = (
                        int(toks[4]) if len(toks) >= 5 and toks[4].isdigit() else 9500
                    )
                    if ING_TASK and not ING_TASK.done():
                        warn("Ingestion already running.")
                        prompt()
                        continue
                    ING_TASK = asyncio.create_task(
                        ingest_synth_loop(path, out, chunk_kb, synth_chars)
                    )
                    ok(f"Started SYNTH ingestion from {path} → {out}")
            elif cmd == "/ingest.lossless":
                toks = line.split()
                if len(toks) < 3:
                    err(
                        "Usage: /ingest.lossless <file> <synth.md> [chunkKB=45] [synthChars=12000]"
                    )
                else:
                    path = toks[1]
                    out = toks[2]
                    chunk_kb = (
                        int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 45
                    )
                    synth_chars = (
                        int(toks[4]) if len(toks) >= 5 and toks[4].isdigit() else 12000
                    )
                    if ING_TASK and not ING_TASK.done():
                        warn("Ingestion already running.")
                        prompt()
                        continue
                    ING_TASK = asyncio.create_task(
                        ingest_synth_loop(path, out, chunk_kb, synth_chars)
                    )
                    ok(f"Started LOSSLESS synthesis from {path} → {out}")
            elif cmd == "/ingest.stop":
                if ING_ON:
                    ING_ON = False
                    ok("Stopping ingestion…")
                else:
                    warn("No ingestion running.")
            elif cmd == "/ingest.status":
                show_status()
            elif cmd == "/style.capture":
                toks = line.split()
                if len(toks) < 3:
                    err(
                        "Usage: /style.capture <file> <style.synth.md> [chunkKB=30] [styleChars=6000]"
                    )
                    prompt()
                    continue
                path, out = toks[1], toks[2]
                chunk_kb = int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 30
                style_chars = (
                    int(toks[4]) if len(toks) >= 5 and toks[4].isdigit() else 6000
                )
                if ING_TASK and not ING_TASK.done():
                    warn("Ingestion already running.")
                    prompt()
                    continue
                ING_TASK = asyncio.create_task(
                    ingest_style_loop(path, out, chunk_kb, style_chars)
                )
                ok(f"Started style capture from {path} → {out}")
            elif cmd == "/style.apply":
                toks = line.split()
                if len(toks) < 3:
                    err(
                        "Usage: /style.apply <style.synth.md> <topic|file> [out.md] [--words=N]"
                    )
                    prompt()
                    continue
                style, topic = toks[1], toks[2]
                out = None
                words = None
                for tk in toks[3:]:
                    if tk.startswith("--words="):
                        try:
                            words = int(tk.split("=", 1)[1])
                        except:
                            pass
                    else:
                        out = tk
                await style_apply(
                    style, topic, out, words=None if not words else int(words)
                )

            elif cmd == "/style.nobs":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                    val = parts[1].strip().lower()
                    global NO_BS_ACTIVE
                    if val == "on" and not NO_BS_ACTIVE:
                        SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
                        set_system(SYSTEM_PROMPT.strip() + "\n\n" + NO_BS_ADDENDUM)
                        NO_BS_ACTIVE = True
                        ok("No‑bullshit language ON (session).")
                    elif val == "off" and NO_BS_ACTIVE:
                        if SAVE_SYSTEM_STACK:
                            set_system(SAVE_SYSTEM_STACK.pop())
                        NO_BS_ACTIVE = False
                        ok("No‑bullshit language OFF.")
                    else:
                        warn("Already in desired state.")
                else:
                    err("Usage: /style.nobs on|off")

            elif cmd == "/style.narrative":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                    val = parts[1].strip().lower()
                    global NARRATIVE_ACTIVE
                    if val == "on" and not NARRATIVE_ACTIVE:
                        SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
                        set_system(
                            (SYSTEM_PROMPT.strip() + "\n\n" + NARRATIVE_OVERLAY).strip()
                        )
                        NARRATIVE_ACTIVE = True
                        ok("Narrative + pedagogy overlay ON (session).")
                    elif val == "off" and NARRATIVE_ACTIVE:
                        if SAVE_SYSTEM_STACK:
                            set_system(SAVE_SYSTEM_STACK.pop())
                        NARRATIVE_ACTIVE = False
                        ok("Narrative + pedagogy overlay OFF.")
                    else:
                        warn("Already in desired state.")
                else:
                    err("Usage: /style.narrative on|off")

            # Density and continuation knobs (exposed in PTK path as well)
            elif cmd == "/book.hammer":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                    COVERAGE_HAMMER_ON = parts[1].strip().lower() == "on"
                    ok(f"Self-study continuation hammer: {COVERAGE_HAMMER_ON}")
                else:
                    err("Usage: /book.hammer on|off")

            elif cmd == "/out.budget":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                    OUTPUT_BUDGET_SNIPPET_ON = parts[1].strip().lower() == "on"
                    ok(f"OUTPUT_BUDGET addendum: {OUTPUT_BUDGET_SNIPPET_ON}")
                else:
                    err("Usage: /out.budget on|off")

            elif cmd == "/out.push":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                    OUTPUT_PUSH_ON = parts[1].strip().lower() == "on"
                    ok(f"Output push: {OUTPUT_PUSH_ON}")
                else:
                    err("Usage: /out.push on|off")

            elif cmd == "/out.minchars":
                if len(parts) >= 2:
                    try:
                        v = int(parts[1])
                        if v < 1000:
                            warn("Value too small; suggest >= 2500.")
                        OUTPUT_MIN_CHARS = max(1000, v)
                        ok(f"OUTPUT_MIN_CHARS={OUTPUT_MIN_CHARS}")
                    except:
                        err("Provide an integer.")
                else:
                    err("Usage: /out.minchars <N>")

            elif cmd == "/out.passes":
                if len(parts) >= 2:
                    try:
                        v = int(parts[1])
                        if v < 0 or v > 10:
                            warn("Unusual value; using within [0..10].")
                        OUTPUT_PUSH_MAX_PASSES = max(0, min(10, v))
                        ok(f"OUTPUT_PUSH_MAX_PASSES={OUTPUT_PUSH_MAX_PASSES}")
                    except:
                        err("Provide an integer.")
                else:
                    err("Usage: /out.passes <N>")

            # Rewrite/Lossless
            elif cmd == "/rewrite.start":
                toks = line.split()
                if len(toks) < 3:
                    err("Usage: /rewrite.start <synth.md> <out.md>")
                else:
                    await rewrite_start(toks[1], toks[2])
            elif cmd == "/rewrite.lossless":
                toks = line.split()
                if len(toks) < 2:
                    err("Usage: /rewrite.lossless <synth.md> [out.md]")
                else:
                    synth = toks[1]
                    out = toks[2] if len(toks) >= 3 else None
                    await rewrite_lossless(synth, out)

            # One-shot lossless pipeline
            elif cmd == "/lossless.run":
                toks = line.split()
                if len(toks) < 2:
                    err(
                        "Usage: /lossless.run <file> [--outdir=DIR] [--chunkKB=45] [--synthChars=12000]"
                    )
                    prompt()
                    continue
                path = toks[1]
                outdir = None
                ck = 45
                sc = 12000
                for tk in toks[2:]:
                    if tk.startswith("--outdir="):
                        outdir = tk.split("=", 1)[1]
                    elif tk.startswith("--chunkKB="):
                        try:
                            ck = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--synthChars="):
                        try:
                            sc = int(tk.split("=", 1)[1])
                        except:
                            pass
                await lossless_run(path, outdir, chunk_kb=ck, synth_chars=sc)

            # NEW: Bilingual and Policy commands
            elif cmd == "/bilingual.file":
                # /bilingual.file <file> --lang=LANG [--outdir=DIR] [--chunkKB=45]
                toks = line.split()
                if len(toks) < 2:
                    err(
                        "Usage: /bilingual.file <file> --lang=LANG [--outdir=DIR] [--chunkKB=45]"
                    )
                else:
                    path = toks[1]
                    lang = None
                    outdir = None
                    ck = 45
                    for tk in toks[2:]:
                        if tk.startswith("--lang="):
                            lang = tk.split("=", 1)[1]
                        elif tk.startswith("--outdir="):
                            outdir = tk.split("=", 1)[1]
                        elif tk.startswith("--chunkKB="):
                            ck = int(tk.split("=", 1)[1])
                    if not lang:
                        err("Provide --lang=LANG")
                    else:
                        await bilingual_transform_file(path, lang, outdir, chunk_kb=ck)

            elif cmd == "/policy.from":
                # /policy.from <reg_file> <out_dir> [--org="..."] [--jurisdiction="..."] [--chunkKB=45] [--synthChars=16000]
                toks = line.split()
                if len(toks) < 3:
                    err(
                        'Usage: /policy.from <reg_file> <out_dir> [--org="..."] [--jurisdiction="..."] [--chunkKB=45] [--synthChars=16000]'
                    )
                else:
                    reg = toks[1]
                    outd = toks[2]
                    org = None
                    juris = None
                    ck = 45
                    sc = 16000
                    for tk in toks[3:]:
                        if tk.startswith("--org="):
                            org = tk.split("=", 1)[1].strip('"')
                        elif tk.startswith("--jurisdiction="):
                            juris = tk.split("=", 1)[1].strip('"')
                        elif tk.startswith("--chunkKB="):
                            ck = int(tk.split("=", 1)[1])
                        elif tk.startswith("--synthChars="):
                            sc = int(tk.split("=", 1)[1])
                    await policy_from_regulations(
                        reg,
                        outd,
                        org=org,
                        jurisdiction=juris,
                        chunk_kb=ck,
                        synth_chars=sc,
                    )

            # Study/Translate
            elif cmd == "/flashcards.from":
                toks = line.split()
                if len(toks) < 3:
                    err("Usage: /flashcards.from <synth.md> <out.md> [n=200]")
                    prompt()
                    continue
                n = int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 200
                await flashcards_from_synth(toks[1], toks[2], n=n)
            elif cmd == "/glossary.from":
                toks = line.split()
                if len(toks) < 3:
                    err("Usage: /glossary.from <synth.md> <out.md>")
                    prompt()
                    continue
                await glossary_from_synth(toks[1], toks[2])
            elif cmd == "/index.from":
                toks = line.split()
                if len(toks) < 3:
                    err("Usage: /index.from <synth.md> <out.md>")
                    prompt()
                    continue
                await index_from_synth(toks[1], toks[2])
            elif cmd == "/translate.file":
                toks = line.split()
                if len(toks) < 3:
                    err("Usage: /translate.file <file> <language> [chunkKB=50]")
                    prompt()
                    continue
                chunk_kb = int(toks[3]) if len(toks) >= 4 and toks[3].isdigit() else 50
                await translate_file(toks[1], " ".join(toks[2:3]), chunk_kb=chunk_kb)
            elif cmd == "/chad":
                # /chad "What is X?" [--depth=short|medium|deep] [--prose] [--norefs] [--nocontra]
                m = re.findall(r'"([^"]+)"', line)
                if not m:
                    err(
                        'Usage: /chad "your question" [--depth=short|medium|deep] [--prose] [--norefs] [--nocontra]'
                    )
                    prompt()
                    continue
                q = m[0]
                depth = "short"
                bullets = True
                refs = True
                contra = True
                for tk in line.split():
                    if tk.startswith("--depth="):
                        depth = tk.split("=", 1)[1].strip().lower()
                    elif tk == "--prose":
                        bullets = False
                    elif tk == "--norefs":
                        refs = False
                    elif tk == "--nocontra":
                        contra = False
                await answer_chad(
                    q, depth=depth, bullets=bullets, refs=refs, contra=contra
                )
                prompt()
                continue

            # Snapshot
            elif cmd == "/snapshot":
                # optional flag: --chunk
                do_chunk = "--chunk" in line or "-c" in line
                args = ["bash", "snapshot.sh"]
                if do_chunk:
                    args.append("--chunk")
                try:
                    subprocess.run(args, check=False)
                    ok("Snapshot command executed.")
                except Exception as e:
                    err(f"Snapshot failed: {e}")

            # Prompt Booster commands
            elif cmd == "/prompt.boost":
                # /prompt.boost "goal" [--ask] [--apply] [--meta]
                m = re.findall(r'"([^"]+)"', line)
                if not m:
                    err('Usage: /prompt.boost "your goal" [--ask] [--apply] [--meta]')
                    prompt()
                    continue
                goal = m[0]
                ask = "--ask" in line
                meta = "--meta" in line
                pr = await prompt_boost(goal, ask=ask or True, meta=meta)
                if ("--apply" in line) and BOOST_LAST_PROMPT:
                    prompt_apply("next")

            elif cmd == "/prompt.answer":
                # multiline answers
                ans = await read_multiline(
                    "Paste answers (number or bullet wise). End with: EOF"
                )
                if ans.strip():
                    await prompt_answer(ans)
                else:
                    warn("No answers provided.")

            elif cmd == "/prompt.apply":
                where = "next"
                if len(parts) >= 2 and parts[1].strip().lower() in ("next", "system"):
                    where = parts[1].strip().lower()
                prompt_apply(where)

            # Recipe runner commands
            elif cmd == "/run.recipe":
                toks = line.split()
                if len(toks) < 2:
                    err("Usage: /run.recipe <recipe.(json|yml|yaml)>")
                    prompt()
                    continue
                await run_recipe_file(toks[1])

            elif cmd == "/run.quick":
                # fast inline recipe: /run.quick task=book.zero2hero subject="X" out=./books/x.md max=6 style=no-bs,chad
                args = {}
                for tk in line.split()[1:]:
                    if "=" in tk:
                        k, v = tk.split("=", 1)
                        args[k] = v.strip('"')
                rec = {
                    "task": args.get("task", "book.zero2hero"),
                    "subject": args.get("subject"),
                    "styles": (
                        (args.get("style", "") or args.get("styles", "")).split(",")
                        if args.get("style") or args.get("styles")
                        else []
                    ),
                    "io": {"output": "file", "outPath": args.get("out")},
                    "max_chunks": (
                        int(args["max"])
                        if args.get("max") and args["max"].isdigit()
                        else None
                    ),
                }
                await run_recipe(rec)

            # Project/Pipeline
            elif cmd == "/project.init":
                # /project.init [--dir=.]
                dir_path = "."
                for tk in line.split()[1:]:
                    if tk.startswith("--dir="):
                        dir_path = tk.split("=", 1)[1]

                root_dir = os.path.abspath(dir_path)
                lmastudio_dir = os.path.join(root_dir, ".lmastudio")

                ensure_dir(lmastudio_dir)
                ensure_dir(os.path.join(lmastudio_dir, "checkpoints"))
                ensure_dir(os.path.join(lmastudio_dir, "refs"))
                ensure_dir(os.path.join(root_dir, "pipelines"))
                ensure_dir(os.path.join(root_dir, "recipes"))
                ensure_dir(os.path.join(root_dir, "workspace"))
                ensure_dir(os.path.join(root_dir, "outputs"))
                ensure_dir(os.path.join(root_dir, "books"))

                # Create project.yml placeholder
                proj_yml_path = os.path.join(lmastudio_dir, "project.yml")
                if not os.path.exists(proj_yml_path):
                    with open(proj_yml_path, "w", encoding="utf-8") as f:
                        f.write("default_backend: bridge\n")
                        f.write("default_model: null\n")
                        f.write("paths:\n")
                        f.write("  workspace: workspace/\n")
                        f.write("  outputs: outputs/\n")

                ok(f"Project scaffold created in: {root_dir}")

            elif cmd == "/pipeline.run":
                toks = line.split()
                if len(toks) < 2:
                    err("Usage: /pipeline.run <pipeline.yml>")
                    prompt()
                    continue
                if not PipelineExecutor:
                    err(
                        "PipelineExecutor not available. Check imports and dependencies."
                    )
                    prompt()
                    continue

                # Pass self (the current module/context) to the executor for callbacks
                executor = PipelineExecutor(sys.modules[__name__], ok, warn, err)
                await executor.execute_pipeline(toks[1])

            # Checkpoint commands
            elif cmd == "/book.save":
                # /book.save [name]
                name = parts[1] if len(parts) >= 2 else None
                await book_save(name)

            elif cmd == "/book.load":
                # /book.load <name>
                if len(parts) < 2:
                    err("Usage: /book.load <name>")
                    prompt()
                    continue
                await book_load(parts[1])

            # Macro commands
            elif cmd == "/macro.save":
                # /macro.save <name> <command template>
                toks = line.split(maxsplit=2)
                if len(toks) < 3:
                    err('Usage: /macro.save <name> "<command template>"')
                    prompt()
                    continue
                name = toks[1]
                template = toks[2].strip().strip('"')
                MACROS[name] = template
                _save_macros()
                ok(f"Macro '{name}' saved.")

            elif cmd == "/macro.list":
                if not MACROS:
                    warn("No macros defined.")
                    prompt()
                    continue
                print(hr())
                print("Macros:")
                for name, template in MACROS.items():
                    print(f"  {name}: {template}")
                print(hr())

            elif cmd == "/macro.delete":
                if len(parts) < 2:
                    err("Usage: /macro.delete <name>")
                    prompt()
                    continue
                name = parts[1]
                if name in MACROS:
                    del MACROS[name]
                    _save_macros()
                    ok(f"Macro '{name}' deleted.")
                else:
                    warn(f"Macro '{name}' not found.")

            elif cmd == "/macro.run":
                # /macro.run <name> [arg1 arg2 ...]
                toks = line.split()
                if len(toks) < 2:
                    err("Usage: /macro.run <name> [args...]")
                    prompt()
                    continue
                name = toks[1]
                args = toks[2:]

                command = _run_macro(name, args)
                if command:
                    ok(f"Running macro: {command}")
                    # Recursively call _handle_command with the expanded command
                    await _handle_command(command)

            # Manual autopilot
            elif cmd == "/book.start" and len(parts) >= 2:
                AUTO_OUT = parts[1]
                AUTO_ON = True
                AUTO_COUNT = 0
                LAST_NEXT_HINT = None
                ok(f"Autopilot ON → {AUTO_OUT}")
                if AUTO_TASK and not AUTO_TASK.done():
                    AUTO_TASK.cancel()
                AUTO_TASK = asyncio.create_task(autorun_loop())
            elif cmd == "/book.stop":
                AUTO_ON = False
                ok("Autopilot OFF.")
            elif cmd == "/book.max" and len(parts) >= 2:
                try:
                    n = int(parts[1])
                    AUTO_MAX = None if n <= 0 else n
                    ok(f"Auto max={AUTO_MAX or '(unlimited)'}")
                except:
                    err("Provide an integer.")
            elif cmd == "/book.status":
                show_status()

            # Misc
            elif cmd == "/mono":
                global USE_COLOR
                USE_COLOR = not USE_COLOR
                _apply_colors()
                ok(f"Monochrome {'ON' if not USE_COLOR else 'OFF'}.")
            elif cmd == "/image":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                    global IMAGE_MARKDOWN
                    IMAGE_MARKDOWN = parts[1].strip().lower() == "on"
                    ok(f"Images → {IMAGE_MARKDOWN}")
                else:
                    err("Usage: /image on|off")
            elif cmd == "/clear":
                HISTORY.clear()
                ok("History cleared.")
            elif cmd == "/history.tail":
                try:
                    u = next(
                        (m for m in reversed(HISTORY) if m["role"] == "user"), None
                    )
                    a = next(
                        (m for m in reversed(HISTORY) if m["role"] == "assistant"), None
                    )
                    print(hr())
                    if u:
                        print(
                            f"Last user: {u['content'][:500] + ('...' if len(u['content'])>500 else '')}"
                        )
                    if a:
                        print(
                            f"Last assistant: {a['content'][:500] + ('...' if len(a['content'])>500 else '')}"
                        )
                    print(hr())
                except Exception as e:
                    err(f"history.tail failed: {e}")
            elif cmd == "/cont.mode":
                if len(parts) >= 2 and parts[1].strip().lower() in ("normal", "anchor"):
                    CONT_MODE = parts[1].strip().lower()
                    ok(f"Continuation mode: {CONT_MODE}")
                else:
                    err("Usage: /cont.mode [normal|anchor]")

            elif cmd == "/cont.anchor":
                if len(parts) >= 2:
                    try:
                        n = int(parts[1])
                        if n < 50 or n > 2000:
                            warn("Choose a value between 50 and 2000.")
                        else:
                            CONT_ANCHOR_CHARS = n
                            ok(f"Anchor length: {CONT_ANCHOR_CHARS}")
                    except:
                        err("Provide an integer.")
                else:
                    err("Usage: /cont.anchor <N>")

            elif cmd == "/repeat.warn":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on", "off"):
                    REPEAT_WARN = parts[1].strip().lower() == "on"
                    ok(f"Repeat warn: {REPEAT_WARN}")
                else:
                    err("Usage: /repeat.warn on|off")

            elif cmd == "/repeat.thresh":
                if len(parts) >= 2:
                    try:
                        t = float(parts[1])
                        if t <= 0 or t >= 1:
                            warn("Use a value between 0 and 1 (e.g., 0.35).")
                        else:
                            REPEAT_THRESH = t
                            ok(f"Repeat threshold: {REPEAT_THRESH}")
                    except:
                        err("Provide a float (0..1).")
                else:
                    err("Usage: /repeat.thresh <0..1>")

            elif cmd == "/debug.cont":
                anch = continuation_anchor(CONT_ANCHOR_CHARS)
                print(hr())
                print(f"Anchor ({len(anch)} chars): {anch!r}")
                print(f"LAST_NEXT_HINT: {LAST_NEXT_HINT!r}")
                print(hr())

            elif cmd == "/debug.ctx":
                ctx = trimmed_history()
                print(hr())
                print(f"Context messages included: {len(ctx)}")
                if ctx:
                    print(
                        f"First in ctx: {ctx[0]['role']} … Last in ctx: {ctx[-1]['role']}"
                    )
                print(hr())
            else:
                warn("Unknown command. /help for help.")
            return

        # manual chat
        if AUTO_ON:
            warn(
                "Autopilot running. Use /book.pause and /next to intervene, or /book.stop to stop."
            )
            return
        try:
            await ask_collect(line)
        except Exception as e:
            err(f"Error: {e}")


# ---------------- CLI loop ----------------
async def repl_prompt_toolkit():
    global CANCEL_REQUESTED, AUTO_PAUSE
    if not PTK_AVAILABLE:
        warn("prompt_toolkit not available. Falling back to simple input.")
        return await repl_fallback()

    session = PromptSession()
    kb = KeyBindings()

    @kb.add("c-c")
    def _(event):  # Ctrl+C
        # Set cancel flag but don't exit the prompt - let the main loop handle it
        globals()["CANCEL_REQUESTED"] = True
        event.cli.exit()  # Exit current prompt to return control to main loop

    @kb.add("c-x")
    def _(event):  # Ctrl+X -> exit
        # Set a flag to indicate exit was requested via Ctrl+X
        globals()["PTK_CTRL_X_EXIT"] = True
        event.cli.exit()  # Exit the prompt session to return control to the main loop

    @kb.add("c-p")
    def _(event):  # Ctrl+P -> pause after current
        globals()["AUTO_PAUSE"] = True
        print("\n[set autopause ON]")

    @kb.add("c-s")
    def _(event):  # Ctrl+S -> /status
        print()
        asyncio.create_task(_handle_command("/status"))

    help_text()
    prompt()
    while True:
        try:
            line = await session.prompt_async("> ", key_bindings=kb)
        except (EOFError, KeyboardInterrupt):
            # Ctrl+D or Ctrl+C in prompt (if not handled by keybinding)
            # Check if exit was requested via Ctrl+X
            if globals().get("PTK_CTRL_X_EXIT"):
                globals().pop("PTK_CTRL_X_EXIT", None)
                raise SystemExit(0)  # Exit because of Ctrl+X
            elif CANCEL_REQUESTED:
                CANCEL_REQUESTED = False  # Clear flag if it was set by keybinding
                continue
            raise SystemExit(0)

        if line is None:
            # This can happen when exit() is called on the prompt session
            if globals().get("EXIT_REQUESTED"):
                # This was a Ctrl+X exit request
                globals().pop("EXIT_REQUESTED", None)
                globals().pop("CANCEL_REQUESTED", None)  # Clean up
                raise SystemExit(0)  # Exit properly
            elif globals().get("CANCEL_REQUESTED"):
                # This was a Ctrl+C cancel request - just continue the loop
                CANCEL_REQUESTED = False
                continue
            continue
        if line is None:
            # This can happen when exit() is called on the prompt session
            if globals().get("PTK_CTRL_X_EXIT"):
                # This was a Ctrl+X exit request
                globals().pop("PTK_CTRL_X_EXIT", None)
                raise SystemExit(0)  # Exit properly
            if CANCEL_REQUESTED:
                # This was a Ctrl+C cancel request - just continue the loop
                CANCEL_REQUESTED = False  # Clear the flag
                continue
            continue
        elif globals().get("PTK_CTRL_X_EXIT"):
            # Handle case where Ctrl+X was pressed and we have a line
            globals().pop("PTK_CTRL_X_EXIT", None)
            raise SystemExit(0)
        elif CANCEL_REQUESTED:  # Handle Ctrl+C cancel request
            CANCEL_REQUESTED = False  # Clear the flag
            raise SystemExit(0)  # This is for the exception handler case

        # Handle command/chat
        await _handle_command(line)
        prompt()


async def repl_fallback():
    help_text()
    prompt()
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        line = line.rstrip("\n")
        if not line.strip():
            prompt()
            continue

        await _handle_command(line)
        prompt()


async def repl():
    # Check environment variable LMA_USE_PTK=1 to enable PTK
    use_ptk = os.getenv("LMA_USE_PTK", "1") == "1" and PTK_AVAILABLE
    if use_ptk:
        await repl_prompt_toolkit()
    else:
        await repl_fallback()


# ---------------- App bootstrap ----------------
def start_interactive():
    main()
