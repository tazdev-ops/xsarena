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
import uuid
import re
import sys
import shutil
import os
try:
    from openai import OpenAI as _OpenAIClient
except Exception:
    _OpenAIClient = None
from datetime import datetime
from aiohttp import web

# ---------------- Colors/UI ----------------
USE_COLOR = sys.stdout.isatty()
class C:
    R=""; B=""; DIM=""; OK=""; WARN=""; ERR=""; USER=""; ASSIST=""; INFO=""
def _apply_colors():
    if not USE_COLOR:
        for k in list(C.__dict__.keys()):
            if k.isupper(): setattr(C, k, "")
        return
    C.R="\x1b[0m"; C.B="\x1b[1m"; C.DIM="\x1b[2m"
    C.OK="\x1b[32m"; C.WARN="\x1b[33m"; C.ERR="\x1b[31m"
    C.USER="\x1b[38;5;39m"; C.ASSIST="\x1b[38;5;190m"; C.INFO="\x1b[38;5;244m"
_apply_colors()
def hr(ch="-"): return ch * max(20, min(shutil.get_terminal_size((80,20)).columns, 120))
def now(): return datetime.now().strftime("%H:%M:%S")
def info(msg): print(f"{C.INFO}{msg}{C.R}")
def ok(msg): print(f"{C.OK}{msg}{C.R}")
def warn(msg): print(f"{C.WARN}{msg}{C.R}")
def err(msg): print(f"{C.ERR}{msg}{C.R}")

# ---------------- Basic utils ----------------
BOOKS_DIR = "books"

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s or "book"

def next_available_path(base_path: str) -> str:
    if not os.path.exists(base_path):
        return base_path
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root, ext = os.path.splitext(base_path)
    return f"{root}-{stamp}{ext or '.md'}"

# ---------------- Bridge state ----------------
PENDING_JOBS = []           # [{request_id, payload}]
RESPONSE_CHANNELS = {}      # req_id -> asyncio.Queue
CAPTURE_FLAG = False
CLIENT_SEEN = False

# ---------------- Chat state ----------------
SESSION_ID = ""
MESSAGE_ID = ""
MODEL_ID = None
SYSTEM_PROMPT = ""
HISTORY = []                # [{"role":"user"/"assistant","content":...}]
HISTORY_WINDOW = 80         # last N exchanges (user+assistant=2)

# ---------------- No-Bullshit additions ----------------
NO_BS_ACTIVE = False
NO_BS_ADDENDUM = """LANGUAGE CONSTRAINTS
- Plain, direct language; avoid pompous terms and circumlocutions.
- Prefer short sentences and concrete nouns/verbs.
- Remove throat‑clearing, meta commentary, and rhetorical filler."""

# ---------------- Autopilot ----------------
AUTO_ON = False
AUTO_TASK = None
AUTO_OUT = None
AUTO_COUNT = 0
AUTO_MAX = None
AUTO_DELAY = 1.0
LAST_NEXT_HINT = None
SAVE_SYSTEM_STACK: list[str] = []  # push/pop system alters
NEXT_OVERRIDE: str | None = None   # one-shot override for the next prompt
AUTO_PAUSE = False                 # pause autopilot after finishing a chunk

# --- Self-study continuation hammer ---
SESSION_MODE = None               # e.g., "zero2hero", None otherwise
COVERAGE_HAMMER_ON = True         # when True, add a minimal anti-wrap-up line to continue prompts

# --- Output budget / push-to-max controls ---
OUTPUT_BUDGET_SNIPPET_ON = True   # append system prompt addendum on book modes
OUTPUT_PUSH_ON = True             # auto-extend within the same subtopic to hit a min length
OUTPUT_MIN_CHARS = 4500           # target minimal chunk size before moving on (tune as needed)
OUTPUT_PUSH_MAX_PASSES = 3        # at most N extra "continue within current subtopic" micro-steps

# --- Cloudflare controls ---
CF_BLOCKED = False       # true while CF challenge is active
CF_NOTIFIED = False      # ensure we print the notice only once per CF event

# --- Backend switch ---
BACKEND = "bridge"  # bridge | openrouter

# --- OpenRouter config/state ---
OR_CLIENT = None
OR_MODEL = os.getenv("OPENROUTER_MODEL")  # e.g., "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
OR_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OR_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
OR_REFERRER = os.getenv("OPENROUTER_REFERRER")  # optional
OR_TITLE = os.getenv("OPENROUTER_TITLE")        # optional
OR_HEADERS = None  # built in init

# --- Continuation controls ---
CONT_MODE = "anchor"      # "anchor" (default) or "normal"
CONT_ANCHOR_CHARS = 200   # how many chars from the end of last assistant chunk to use as anchor
REPEAT_WARN = True        # warn and auto-pause if high repetition detected
REPEAT_NGRAM = 4          # n-gram size for repetition scoring
REPEAT_THRESH = 0.35      # Jaccard threshold to warn (0..1); lower = more sensitive

# ---------------- Ingestion/Synthesis ----------------
ING_ON = False
ING_TASK = None
ING_MODE = None             # "ack", "synth", "style"
ING_PATH = None
ING_POS = 0
ING_TOTAL = 0
ING_CHUNK_BYTES = 0
SYNTH_TEXT = ""
SYNTH_LIMIT = 9500
SYNTH_OUT = None

# ---------------- Parsers ----------------
ERROR_RE = re.compile(r'(\{\s*"error".*?\})', re.DOTALL)
FINISH_RE = re.compile(r'[ab]d:(\{.*?"finishReason".*?\})', re.DOTALL)
CF_PATTERNS = [r'<title>Just a moment...</title>', r'Enable JavaScript and cookies to continue']
NEXT_RE = re.compile(r'^\s*NEXT:\s*(.+)\s*$', re.MULTILINE)

def extract_text_chunks(buf: str):
    out=[]
    while True:
        m = re.search(r'[ab]0:"', buf)
        if not m: break
        start = m.end()
        i = start
        while True:
            j = buf.find('"', i)
            if j == -1:
                return out, buf
            # count preceding backslashes
            bs=0; k=j-1
            while k>=0 and buf[k]=='\\':
                bs+=1; k-=1
            if bs % 2 == 0:
                esc = buf[start:j]
                try:
                    txt = json.loads('"'+esc+'"')
                    if txt: out.append(txt)
                except Exception: pass
                buf = buf[j+1:]
                break
            else:
                i = j+1
    return out, buf

def strip_next_marker(text: str):
    hint=None; last=None
    for m in NEXT_RE.finditer(text): last=m
    if last:
        hint = last.group(1).strip()
        text = text[:last.start()] + text[last.end():]
    return text.rstrip(), hint

def last_assistant_text() -> str:
    for m in reversed(HISTORY):
        if m["role"] == "assistant":
            return m["content"] or ""
    return ""

def continuation_anchor(tail_chars: int) -> str:
    prev = last_assistant_text()
    if not prev:
        return ""
    s = prev[-tail_chars:]
    # trim to sentence boundary if possible
    p = max(s.rfind("."), s.rfind("!"), s.rfind("?"))
    if p != -1 and p >= len(s) - 120:  # try to end on sentence end near the tail
        s = s[:p+1]
    return s.strip()

def anchor_from_text(txt: str, tail_chars: int) -> str:
    if not txt:
        return ""
    s = txt[-tail_chars:]
    p = max(s.rfind("."), s.rfind("!"), s.rfind("?"))
    if p != -1 and p >= len(s) - 120:
        s = s[:p+1]
    return s.strip()

def jaccard_ngrams(a: str, b: str, n: int = 4) -> float:
    def ngrams(x):
        x = re.sub(r"\s+", " ", x.strip())
        return set([x[i:i+n] for i in range(0, max(0, len(x)-n+1))])
    A, B = ngrams(a), ngrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)

def build_anchor_continue_prompt(anchor: str) -> str:
    # A compact, subject-free continuation instruction
    return (
        "Continue exactly from after the following anchor. Do not repeat the anchor. "
        "Do not reintroduce the subject or previous headings; do not summarize; pick up mid-paragraph if needed.\n"
        "ANCHOR:\n<<<ANCHOR\n" + anchor + "\nANCHOR>>>\n"
        "Continue."
    )

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
    resp = {"hello":True, "capture":CAPTURE_FLAG, "job":None}
    if CAPTURE_FLAG: CAPTURE_FLAG=False
    if PENDING_JOBS: resp["job"] = PENDING_JOBS.pop(0)
    if first:
        print(); ok(f"[{now()}] Browser polling active."); print("> ", end="", flush=True)
    return _add_cors(web.json_response(resp))

async def bridge_push(request: web.Request):
    try:
        data = await request.json()
        req_id = data.get("request_id"); payload = data.get("data")
        if not req_id: return _add_cors(web.json_response({"error":"missing request_id"}, status=400))
        q = RESPONSE_CHANNELS.get(req_id)
        if q: await q.put(payload)
        return _add_cors(web.json_response({"status":"ok"}))
    except Exception as e:
        return _add_cors(web.json_response({"error":str(e)}, status=500))

# ---------------- ID capture ----------------
async def id_capture_update(request: web.Request):
    global SESSION_ID, MESSAGE_ID
    if request.method=="OPTIONS": return _add_cors(web.Response(text=""))
    try:
        data = await request.json()
        sid, mid = data.get("sessionId"), data.get("messageId")
        if not (sid and mid):
            return _add_cors(web.json_response({"error":"missing sessionId or messageId"}, status=400))
        SESSION_ID, MESSAGE_ID = sid, mid
        print(); ok(f"[{now()}] IDs updated:")
        print(f"    session_id = {SESSION_ID}\n    message_id = {MESSAGE_ID}")
        print("> ", end="", flush=True)
        return _add_cors(web.json_response({"status":"ok"}))
    except Exception as e:
        return _add_cors(web.json_response({"error":str(e)}, status=500))

# ---------------- Health ----------------
async def healthz(_req): return web.json_response({"status":"ok"})

# ---------------- Chat payload helpers ----------------
def trimmed_history():
    if HISTORY_WINDOW <= 0: return []
    n = HISTORY_WINDOW*2
    return HISTORY[-n:] if len(HISTORY)>n else HISTORY

def build_payload(user_text: str) -> dict:
    templates=[]
    if SYSTEM_PROMPT.strip():
        templates.append({"role":"system","content":SYSTEM_PROMPT,"attachments":[],"participantPosition":"b"})
    for m in trimmed_history():
        templates.append({"role":m["role"],"content":m["content"],"attachments":[],"participantPosition":"a"})
    templates.append({"role":"user","content":user_text,"attachments":[],"participantPosition":"a"})
    return {"message_templates":templates, "target_model_id":MODEL_ID,
            "session_id":SESSION_ID, "message_id":MESSAGE_ID, "is_image_request":False}

def build_payload_custom(messages: list[dict]) -> dict:
    templates=[]
    for m in messages:
        pos = "b" if m["role"]=="system" else "a"
        templates.append({"role":m["role"],"content":m["content"],"attachments":[],"participantPosition":pos})
    return {"message_templates":templates, "target_model_id":MODEL_ID,
            "session_id":SESSION_ID, "message_id":MESSAGE_ID, "is_image_request":False}

async def send_and_collect(payload: dict, silent: bool=False) -> str:
    global CF_BLOCKED, CF_NOTIFIED
    # Backend switch
    if BACKEND == "openrouter":
        return await _send_and_collect_openrouter(payload, silent=silent)
    if not CLIENT_SEEN:
        warn("No browser polling detected. Open https://lmarena.ai with the userscript enabled."); return ""
    if not SESSION_ID or not MESSAGE_ID:
        warn("Missing session/message IDs. Use /capture then click Retry in LMArena, or /setids."); return ""

    req_id = str(uuid.uuid4())
    q: asyncio.Queue = asyncio.Queue()
    RESPONSE_CHANNELS[req_id] = q
    PENDING_JOBS.append({"request_id":req_id, "payload":payload})

    buf=""; parts=[]
    if not silent: print(f"{C.ASSIST}{C.B}Assistant{C.R}: ", end="", flush=True)
    try:
        while True:
            chunk = await asyncio.wait_for(q.get(), timeout=180.0)
            if isinstance(chunk, dict) and "error" in chunk:
                msg = str(chunk["error"])
                if "401" in msg or "m2m" in msg.lower() or "auth" in msg.lower():
                    if not silent: print(f"\n{C.WARN}! Auth not captured. Click Retry once in LMArena, then try again.{C.R}")
                else:
                    if not silent: print(f"\n{C.ERR}! Error: {msg}{C.R}")
                break
            if chunk == "[DONE]": break
            buf += str(chunk)

            for p in CF_PATTERNS:
                if re.search(p, buf, re.IGNORECASE):
                    # Set CF flags once; avoid repeated prints
                    CF_BLOCKED = True
                    if not CF_NOTIFIED and not silent:
                        print(f"\n{C.WARN}Cloudflare detected. Pausing nicely.{C.R}")
                        print(f"{C.INFO}Please switch to the browser, complete the challenge, then run /cf.resume (and /book.resume if paused).{C.R}")
                        CF_NOTIFIED = True
                    RESPONSE_CHANNELS.pop(req_id, None)
                    return "".join(parts)

            m = ERROR_RE.search(buf)
            if m:
                try:
                    errj = json.loads(m.group(1))
                    if not silent: print(f"\n{C.ERR}! LMArena error: {errj.get('error')}{C.R}")
                    RESPONSE_CHANNELS.pop(req_id, None); return "".join(parts)
                except Exception: pass

            texts, buf = extract_text_chunks(buf)
            for t in texts:
                parts.append(t)
                if not silent: print(t, end="", flush=True)

            mf = FINISH_RE.search(buf)
            if mf: buf = buf[mf.end():]
    except asyncio.TimeoutError:
        if not silent: print(f"\n{C.WARN}! Timed out waiting for response.{C.R}")

    if not silent: print()
    RESPONSE_CHANNELS.pop(req_id, None)
    return "".join(parts)

# ---------------- Public chat helpers ----------------
async def ask_collect(user_text: str):
    print(); print(f"{C.USER}{C.B}You{C.R}: {user_text}\n")
    reply = await send_and_collect(build_payload(user_text))
    print(hr())
    HISTORY.append({"role":"user","content":user_text})
    HISTORY.append({"role":"assistant","content":reply})
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
        raise RuntimeError("openai package not installed. Run: pip install 'openai>=1.20.0'")
    if not OR_API_KEY:
        raise RuntimeError("Missing API key. Set OPENROUTER_API_KEY or OPENAI_API_KEY in your environment.")
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

async def _send_and_collect_openrouter(payload: dict, silent: bool=False) -> str:
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
        body, hint = strip_next_marker(reply)   # strip NEXT from main body; capture hint
        LAST_NEXT_HINT = hint

        # Auto-extend within the same subtopic to hit OUTPUT_MIN_CHARS
        accumulated = body
        local_hint = hint
        micro = 0
        while OUTPUT_PUSH_ON and len(accumulated) < OUTPUT_MIN_CHARS and micro < OUTPUT_PUSH_MAX_PASSES and AUTO_ON:
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
            ext_body, ext_hint = strip_next_marker(ext_reply)  # strip any premature NEXT
            if not ext_body.strip():
                break
            # Optional repetition guard: stop if highly repetitive vs last portion
            if REPEAT_WARN:
                prev_tail = anchor_from_text(accumulated, min(800, CONT_ANCHOR_CHARS*4))
                rep = jaccard_ngrams(prev_tail, ext_body[:max(400, CONT_ANCHOR_CHARS)], n=REPEAT_NGRAM)
                if rep > REPEAT_THRESH:
                    warn(f"High repetition during extension (Jaccard~{rep:.2f}). Stopping extend; you may /next steer.")
                    break
            accumulated += ("\n\n" if not accumulated.endswith("\n") else "") + ext_body
            if ext_hint:    # keep only the last NEXT if the final step later adds it
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
            prev_tail = continuation_anchor(min(800, CONT_ANCHOR_CHARS*4))
            rep = jaccard_ngrams(prev_tail, final_body[:max(400, CONT_ANCHOR_CHARS)], n=REPEAT_NGRAM)
            if rep > REPEAT_THRESH:
                warn(f"High repetition detected (Jaccard~{rep:.2f}). Auto-pausing. Use /next to steer or /book.resume.")
                AUTO_PAUSE = True

        AUTO_COUNT += 1

        # Stop on explicit END
        if final_hint and final_hint.upper() in {"END", "DONE", "STOP", "FINISHED"}:
            ok(f"NEXT: [{final_hint}] — stopping.")
            AUTO_ON = False
            break

        # Carry hint forward (we do not inject hint text into the next prompt, we rely on anchors)
        LAST_NEXT_HINT = final_hint

        await asyncio.sleep(AUTO_DELAY)

    ok(f"Autopilot finished after {AUTO_COUNT} chunk(s). Output: {AUTO_OUT or '(none)'}")
    if SAVE_SYSTEM_STACK:
        sys_old = SAVE_SYSTEM_STACK.pop()
        set_system(sys_old)

# ---------------- Chunking helpers ----------------
def chunks_by_bytes(text: str, max_bytes: int):
    b = text.encode("utf-8")
    out = []; i = 0; n = len(b)
    while i < n:
        j = min(i + max_bytes, n)
        if j < n:
            k = b.rfind(b"\n", i, j)
            if k == -1: k = b.rfind(b" ", i, j)
            if k != -1 and (j - k) < 2048:
                j = k
        part = b[i:j]
        while True:
            try:
                s = part.decode("utf-8")
                break
            except UnicodeDecodeError:
                part = part[:-1]
        out.append(s); i = j
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
    synth_excerpt = synth_text[-limit_chars:] if len(synth_text) > limit_chars else synth_text
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
    with open(path, "r", encoding="utf-8") as f: text = f.read()
    ING_CHUNK_BYTES = max(8_000, int(chunk_kb*1024))
    parts = chunks_by_bytes(text, ING_CHUNK_BYTES)
    ING_ON=True; ING_MODE="ack"; ING_PATH=path; ING_POS=0; ING_TOTAL=len(parts)
    ok(f"Ingest ACK mode: {ING_TOTAL} chunks (~{chunk_kb} KB each)")
    save_sys = SYSTEM_PROMPT; save_win = HISTORY_WINDOW
    try:
        set_system(INGEST_SYSTEM_ACK); set_window(0)
        for idx, chunk in enumerate(parts, start=1):
            if not ING_ON: break
            msg = ingest_user_ack(idx, len(parts), chunk)
            reply = await send_and_collect(build_payload(msg), silent=True)
            print(f"[{now()}] Chunk {idx}/{len(parts)} ack: {reply.strip()[:50]}")
            ING_POS = idx
    finally:
        set_system(save_sys); set_window(save_win)
        ING_ON=False; ING_MODE=None

async def ingest_synth_loop(path: str, synth_out: str, chunk_kb: int, synth_chars: int):
    global ING_ON, ING_MODE, ING_PATH, ING_POS, ING_TOTAL, ING_CHUNK_BYTES, SYNTH_LIMIT, SYNTH_TEXT, SYNTH_OUT
    with open(path, "r", encoding="utf-8") as f: text=f.read()
    SYNTH_OUT = synth_out; SYNTH_LIMIT = max(3000, int(synth_chars))
    ING_CHUNK_BYTES = max(10_000, int(chunk_kb*1024))
    parts = chunks_by_bytes(text, ING_CHUNK_BYTES)
    ING_ON=True; ING_MODE="synth"; ING_PATH=path; ING_POS=0; ING_TOTAL=len(parts)
    ok(f"Ingest SYNTH mode: {ING_TOTAL} chunks (~{chunk_kb} KB each); synth limit ~{SYNTH_LIMIT} chars")
    SYNTH_TEXT = ""
    save_sys = SYSTEM_PROMPT; save_win = HISTORY_WINDOW
    try:
        set_system(INGEST_SYSTEM_SYNTH); set_window(0)
        for idx, chunk in enumerate(parts, start=1):
            if not ING_ON: break
            msg = ingest_user_synth(idx, len(parts), SYNTH_TEXT, chunk, SYNTH_LIMIT)
            reply = await send_and_collect(build_payload(msg), silent=True)
            SYNTH_TEXT = reply.strip()
            with open(SYNTH_OUT, "w", encoding="utf-8") as f: f.write(SYNTH_TEXT)
            print(f"[{now()}] Synth updated {idx}/{len(parts)} — {len(SYNTH_TEXT)} chars")
            ING_POS = idx
    finally:
        set_system(save_sys); set_window(save_win)
        ING_ON=False; ING_MODE=None
        ok(f"Synthesis saved to: {SYNTH_OUT}")

async def ingest_style_loop(path: str, out_path: str, chunk_kb: int, style_chars: int):
    global ING_ON, ING_MODE, ING_PATH, ING_POS, ING_TOTAL, ING_CHUNK_BYTES
    with open(path, "r", encoding="utf-8") as f: text = f.read()
    ING_CHUNK_BYTES = max(10_000, int(chunk_kb*1024))
    parts = chunks_by_bytes(text, ING_CHUNK_BYTES)
    style_profile = ""
    save_sys = SYSTEM_PROMPT; save_win = HISTORY_WINDOW
    try:
        set_system(INGEST_SYSTEM_STYLE); set_window(0)
        ING_ON=True; ING_MODE="style"; ING_PATH=path; ING_POS=0; ING_TOTAL=len(parts)
        for idx, chunk in enumerate(parts, start=1):
            if not ING_ON: break
            msg = style_user_profile(idx, len(parts), style_profile, chunk, style_chars)
            reply = await send_and_collect(build_payload(msg), silent=True)
            style_profile = reply.strip()
            with open(out_path, "w", encoding="utf-8") as f: f.write(style_profile)
            print(f"[{now()}] Style updated {idx}/{len(parts)} — {len(style_profile)} chars")
            ING_POS = idx
    finally:
        set_system(save_sys); set_window(save_win)
        ING_ON=False; ING_MODE=None
        ok(f"Style profile saved to: {out_path}")

# ---------------- Rewrite from synthesis ----------------
async def rewrite_start(synth_path: str, out_path: str, system_template: str | None = None):
    with open(synth_path, "r", encoding="utf-8") as f: synth = f.read()
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    base_system = SYSTEM_PROMPT
    if system_template:
        base_system = system_template
        # Apply output budget addendum if this is a book lossless rewrite template
        if "book.lossless.rewrite" in str(locals().get('system_template', '')) or len(synth) > 5000:  # heuristic for lossless rewriting
            if OUTPUT_BUDGET_SNIPPET_ON:
                base_system = base_system.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(base_system + "\n\nSOURCE SYNTHESIS (for this session only):\n<<<SYNTHESIS\n" + synth + "\nSYNTHESIS>>>\n")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT
    AUTO_OUT = out_path; AUTO_ON=True; AUTO_COUNT=0; LAST_NEXT_HINT=None
    ok(f"Rewrite autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done(): AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())

# ---------------- New: Chunked generation with system ----------------
async def chunked_generate_with_system(synth_path: str, system_template: str, out_path: str, max_chunks=None):
    with open(synth_path, "r", encoding="utf-8") as f: synth = f.read()
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    base_system = system_template
    set_system(base_system + "\n\nSOURCE SYNTHESIS (for this session only):\n<<<SYNTHESIS\n" + synth + "\nSYNTHESIS>>>\n")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path; AUTO_ON=True; AUTO_COUNT=0; LAST_NEXT_HINT=None
    AUTO_MAX = max_chunks
    ok(f"Chunked generation autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done(): AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())

# ---------------- Prompt repository ----------------
BOOK_ZERO2HERO_TEMPLATE = """SUBJECT: {subject}

ROLE
You are a seasoned practitioner and teacher in [FIELD]. Write a comprehensive, high‑density self‑study manual that takes a serious learner from foundations to a master's‑level grasp and practice.

COVERAGE CONTRACT (do not violate)
- Scope: cover the entire field and its major subfields, theory → methods → applications → pitfalls → practice. Include core debates, default choices (and when to deviate), and limits of claims.
- Depth: build from zero to graduate‑level competence; teach skills, not trivia. Show decisive heuristics, procedures, and failure modes at the point of use.
- No early wrap‑up: do not conclude, summarize, or end before the whole field and subfields are covered to the target depth. Treat "continue." as proceeding exactly where you left off.
- Continuity: pick up exactly where the last chunk stopped; no re‑introductions; no throat‑clearing.

VOICE AND STANCE
- Plain, direct Chomsky‑style clarity. Simple language; expose assumptions; no fluff.
- Be decisive when evidence is clear; label uncertainty crisply. Steelman competing views, then choose a default and reason.

STYLE
- Mostly tight paragraph prose. Use bullets only when a read‑and‑do list is clearer.
- Examples only when they materially clarify a decision or distinction.
- Keep numbers when they guide choices; avoid derivations.

JARGON
- Prefer plain language; on first use, write the full term with a short parenthetical gloss; minimize acronyms.

CONTROVERSIES
- Cover directly. Label strength: [robust] [mixed] [contested]. Present main views; state when each might be right; pick a default and give the reason.

EVIDENCE AND CREDITS
- Name only canonical figures, laws, or must‑know sources when attribution clarifies.

PRACTICALITY
- Weave procedures, defaults/ranges, quick checks, and common failure modes where they matter.
- Include checklists, rubrics, and projects/exercises across the arc.

CONTINUATION & CHUNKING
- Write ~800–1,200 words per chunk; stop at a natural break.
- End every chunk with one line: NEXT: [what comes next] (the next specific subtopic).
- On input continue. resume exactly where you left off, with no repetition or re‑introductions, and end again with NEXT: [...]
- Do not end until the manual is complete. When truly complete, end with: NEXT: [END].

BEGIN
Start now from the foundations upward. No preface or meta; go straight into teaching.
"""

BOOK_PLAN_PROMPT = """Create a chapter-by-chapter outline for the SUBJECT above.
- Numbered chapters from zero-to-advanced (master's-level depth).
- For each chapter: goal in one sentence + key subtopics.
- Keep it compact and high-signal.
End with: NEXT: [Begin Chapter 1]
Return only the outline.
"""

BOOK_REFERENCE_TEMPLATE = """SUBJECT: {subject}

ROLE
You are a senior practitioner writing a reference-style handbook of [FIELD] for working professionals.

GOALS
- Dense, navigable, lookup-first. No stories, no prefaces. Useful immediately.
- Sections per topic: Purpose • Definitions • Defaults/Ranges • Procedures • Checks • Failure modes • Notes.
- Keep it compact; avoid repetition.

CONTROVERSIES
- Label strength [robust]/[mixed]/[contested]. Default choice + when to deviate.

CONTINUATION RULES
- Each chunk reads like a contiguous section. End with: NEXT: [what comes next]. On "continue." resume, no repetition. Finish with NEXT: [END].

BEGIN
Start with the top-level structure, then flow section by section."""

BOOK_POP_TEMPLATE = """SUBJECT: {subject}

ROLE
You are a clear, precise explainer writing a popular-science style book on [FIELD].

GOALS
- Clarity first; judicious use of simple stories only when they reveal mechanism or choice.
- Maintain factual precision; avoid hype. Translate math to intuition.

STYLE
- Short paragraphs, vivid analogies, crisp examples.
- Headings that promise specific value.

CONTROVERSIES
- Present main views, what each explains, default stance + why.

CONTINUATION
- ~1000 words per chunk, end with: NEXT: [what comes next]. Finish with NEXT: [END].

BEGIN
Open with the core question that [FIELD] answers and why it matters."""

EXAM_CRAM_TEMPLATE = """SUBJECT: {subject}

ROLE
You are building an exam-cram booklet: high-yield facts, formulas, pitfalls, and mini-drills.

FORMAT
- Headings: Concept • Key formula(s) • Units • Defaults • Quick check • Pitfalls • Example (1–2 lines)
- Mnemonics only if they help recall.

CONTINUATION
- ~800–1000 words per chunk; end with: NEXT: [what comes next]; finish with NEXT: [END]."""

LOSSLESS_REWRITE_TEMPLATE = """You are rewriting from a lossless synthesis into a wiki-style, dense document.

RULES
- No introductions, no anecdotes. Facts, definitions, constraints, mechanisms.
- Use headings and bullets where clearer; keep prose tight.
- Do not invent new facts; do not drop edge cases.

CONTINUATION
- ~1000 words; end with NEXT: [what comes next]; finish with NEXT: [END]."""

TRANSLATE_TEMPLATE = """You are an expert translator. Target language: {lang}.
- Preserve author intent, precision, and register.
- Prefer plain, modern phrasing in the target language.
- Keep technical terms consistent; translate idioms naturally.
- Output only the translation, no preface or commentary."""

BRAINSTORM_TEMPLATE = """You are a high-signal idea engine.
- Generate concise, original, practical ideas.
- Avoid cliches; push into non-obvious angles and tradeoffs.
- Structure when helpful (themes, constraints, levers).
- Be concrete; include examples or quick tests where it clarifies."""

# --- Chad Mode: maximally candid, evidence-first, no fluff ---
CHAD_TEMPLATE = """ROLE
You are a maximally candid, scientifically literate analyst. Answer the user's question with plain language and evidence-first reasoning. Be decisive when the weight of evidence is clear; state uncertainty crisply when it is not. Do not use pompous language, euphemisms, or throat-clearing. No hedging to avoid social discomfort.

RULES
- Plain, direct sentences. Prefer concrete nouns/verbs. No rhetorical filler.
- Claim → Evidence: attach each important claim to evidence classes (e.g., meta-analyses, systematic reviews, consensus reports, historical data, first-principles reasoning). If evidence is weak or mixed, say so.
- Controversies: briefly steelman the main opposing view, then pick a default with the reason. Tag strength: [robust] [mixed] [contested].
- Don'ts: no slurs; no harassment; no illegal instructions; no doxxing; no calls for violence; no medical/legal/personal advice beyond general information.
- If you lack enough basis, say what data would change your mind ("Decisive test: …").
- If asked for numbers, provide useful ranges or magnitudes with units and assumptions.

OUTPUT
- Default: concise bullets or 1–3 tight paragraphs (configurable).
- If "refs" requested, name canonical sources lightly in-text (e.g., WHO 2021, Cochrane 2019, IPCC AR6) without footnotes.
- End with: Bottom line: <one sentence>.

BEGIN
Wait for the question. Produce only the answer—no preface.
"""

STYLE_TRANSFER_TEMPLATE = """You are applying a captured writing style to new content.

STYLE INPUT
<<<STYLE
{style}
STYLE>>>

RULES
- Match tone, rhythm, vocabulary, sentence length, structure, and typical devices.
- Keep factual precision; avoid copying phrases from style input.

OUTPUT
- Return only the content in this style, no meta commentary."""
# OUTPUT BUDGET ADDENDUM
OUTPUT_BUDGET_ADDENDUM = """OUTPUT BUDGET
- Use the full available output window in each response. Do not hold back or end early.
- If you approach the limit mid-subtopic, stop cleanly (no wrap-up). You will resume exactly where you left off on the next input.
- Do not jump ahead or skip subtopics to stay concise. Continue teaching until the whole field and subfields reach the target depth."""

# NEW TEMPLATES FOR BILINGUAL AND POLICY FEATURES
BOOK_BILINGUAL_TEMPLATE = """SUBJECT: {subject} | TARGET LANGUAGE: {lang}

ROLE
You are writing a bilingual manual of [FIELD] for serious self-learners.

OUTPUT FORMAT
- Interleave English and {lang} line-by-line:
  EN: <English paragraph>
  {lang}: <Translated paragraph>
- Maintain a 1:1 alignment; no extra commentary.

STYLE
- Dense, clear, no fluff. Facts, definitions, mechanisms, procedures.
- Examples only if they clarify decisions.

CONTINUATION
- ~800–1000 words per chunk (sum of both languages). End with: NEXT: [what comes next]. Finish with: NEXT: [END].

BEGIN
Start now; no preface. Foundations first."""

BILINGUAL_TRANSFORM_TEMPLATE = """You are converting English text into bilingual format with {lang}.

FORMAT
- Interleave:
  EN: <original paragraph>
  {lang}: <translation>
- Keep a 1:1 mapping, preserve structure. No extra lines or commentary.

Return only the bilingual text."""

POLICY_GENERATOR_TEMPLATE = """You are generating practical governance docs from regulations.

DOC TYPES
- Policy: principles, scope, roles/responsibilities, definitions, commitments.
- Procedures: stepwise runbooks by role; controls; failure modes; metrics.
- Self-check: checklists with criteria, evidence, scoring guidance.

CONTINUATION
- ~900–1100 words per chunk; end with NEXT: [what comes next]; finish with NEXT: [END].

Use SOURCE SYNTHESIS (provided in system prompt) as the knowledge base. No legal advice; practical guidance."""

NO_BS_TEMPLATE = """SUBJECT: {subject}

ROLE
You are writing a no‑nonsense manual of [FIELD]. Plain language, no pomp, no big words unless they carry precision.

RULES
- Cut intros, anecdotes, fluff. Explain the mechanism, the decision, the constraints.
- Prefer short sentences. Prefer exact terms over buzzwords. Define a term in 1 line; move on.
- Use bullets only when decisions/read‑and‑do lists are clearer than prose.
- If a concept doesn't change action or understanding, omit it.

CONTROVERSIES
- State positions fairly in one breath; then pick a default and say why. Label strength: [robust] [mixed] [contested].

CONTINUATION
- 800–1,000 words per chunk; end with: NEXT: [what comes next]; finish with NEXT: [END].

BEGIN
Start with the most important primitives that everything else builds on. No preface, no throat‑clearing.
"""

PROMPT_REPO = {
    "book.zero2hero": {
        "title": "Zero-to-Hero Self-Study Manual",
        "desc": "Dense, no-nonsense manual from foundations to advanced practice.",
        "system": BOOK_ZERO2HERO_TEMPLATE,
        "placeholders": ["{subject}", "[FIELD]"],
    },
    "book.reference": {
        "title": "Reference Handbook",
        "desc": "Lookup-first, dense handbook.",
        "system": BOOK_REFERENCE_TEMPLATE,
        "placeholders": ["{subject}", "[FIELD]"],
    },
    "book.pop": {
        "title": "Pop-Science Narrative",
        "desc": "Accessible, accurate explainer.",
        "system": BOOK_POP_TEMPLATE,
        "placeholders": ["{subject}", "[FIELD]"],
    },
    "exam.cram": {
        "title": "Exam Cram",
        "desc": "High-yield exam prep booklet.",
        "system": EXAM_CRAM_TEMPLATE,
        "placeholders": ["{subject}", "[FIELD]"],
    },
    "book.lossless.rewrite": {
        "title": "Lossless Rewrite",
        "desc": "Wiki-style rewrite from synthesis.",
        "system": LOSSLESS_REWRITE_TEMPLATE,
        "placeholders": [],
    },
    "translate": {
        "title": "Translator",
        "desc": "Expert translation into a target language.",
        "system": TRANSLATE_TEMPLATE,
        "placeholders": ["{lang}"],
    },
    "brainstorm": {
        "title": "Brainstorm",
        "desc": "High-signal idea generation.",
        "system": BRAINSTORM_TEMPLATE,
        "placeholders": [],
    },
    "style.transfer": {
        "title": "Style Transfer",
        "desc": "Apply captured style to new text.",
        "system": STYLE_TRANSFER_TEMPLATE,
        "placeholders": [],
    },
    # NEW ENTRIES FOR BILINGUAL AND POLICY FEATURES
    "book.bilingual": {
        "title": "Bilingual Book",
        "desc": "Subject-aware bilingual manual with English and target language.",
        "system": BOOK_BILINGUAL_TEMPLATE,
        "placeholders": ["{subject}", "{lang}", "[FIELD]"],
    },
    "bilingual.transform": {
        "title": "Bilingual Transform",
        "desc": "Transform text into bilingual format with target language.",
        "system": BILINGUAL_TRANSFORM_TEMPLATE,
        "placeholders": ["{lang}"],
    },
    "policy.generator": {
        "title": "Policy Generator",
        "desc": "Generate policy/procedures/self-check from regulations.",
        "system": POLICY_GENERATOR_TEMPLATE,
        "placeholders": [],
    },
    "book.nobs": {
        "title": "No‑Bullshit Manual",
        "desc": "Brutally concise, plain language, zero fluff.",
        "system": NO_BS_TEMPLATE,
        "placeholders": ["{subject}", "[FIELD]"],
    },
    "answer.chad": {
        "title": "Chad Mode (Candid Evidence Answer)",
        "desc": "Plain, decisive, evidence-first Q&A; zero fluff; safe but blunt.",
        "system": CHAD_TEMPLATE,
        "placeholders": [],
    },
}

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
        out = out.replace("{"+k2+"}", v)
    # [FIELD] -> subject string
    if "subject" in kw:
        out = out.replace("[FIELD]", kw["subject"])
    return out

# ---------------- Book high-level modes ----------------
async def book_zero2hero(subject: str, plan_first: bool, outdir: str|None, max_chunks: int|None, window: int|None):
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
        write_to_file(outline_path, plan_reply.strip()); ok(f"Saved outline → {outline_path}")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path; AUTO_ON=True; AUTO_COUNT=0; LAST_NEXT_HINT=None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"Book autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done(): AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())

async def book_reference(subject: str, plan_first: bool, outdir: str|None, max_chunks: int|None, window: int|None):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(os.path.join(outdir or BOOKS_DIR, f"{slug}.reference.md"))
    outline_path = os.path.join(outdir or BOOKS_DIR, f"{slug}.reference.outline.md")
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_text = repo_render("book.reference", subject=subject)
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_text = sys_text.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(sys_text)
    if window is not None: set_window(window)
    if plan_first:
        plan = "Sketch the top-level sections and subsections for the reference handbook. End with NEXT: [Start Section 1]."
        plan_reply = await send_and_collect(build_payload(plan))
        write_to_file(outline_path, plan_reply.strip()); ok(f"Saved outline → {outline_path}")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path; AUTO_ON=True; AUTO_COUNT=0; LAST_NEXT_HINT=None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"Reference autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done(): AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())

async def book_pop(subject: str, plan_first: bool, outdir: str|None, max_chunks: int|None, window: int|None):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(os.path.join(outdir or BOOKS_DIR, f"{slug}.pop.md"))
    outline_path = os.path.join(outdir or BOOKS_DIR, f"{slug}.pop.outline.md")
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_text = repo_render("book.pop", subject=subject)
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_text = sys_text.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(sys_text)
    if window is not None: set_window(window)
    if plan_first:
        plan = "Draft a compelling, accurate chapter plan for the pop-science book. One line per chapter goal. End with NEXT: [Begin Chapter 1]."
        plan_reply = await send_and_collect(build_payload(plan))
        write_to_file(outline_path, plan_reply.strip()); ok(f"Saved outline → {outline_path}")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path; AUTO_ON=True; AUTO_COUNT=0; LAST_NEXT_HINT=None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"Pop-science autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done(): AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())

async def exam_cram(subject: str, outdir: str|None, max_chunks: int|None, window: int|None):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(os.path.join(outdir or BOOKS_DIR, f"{slug}.cram.md"))
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_text = repo_render("exam.cram", subject=subject)
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_text = sys_text.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(sys_text)
    if window is not None: set_window(window)
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path; AUTO_ON=True; AUTO_COUNT=0; LAST_NEXT_HINT=None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"Exam-cram autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done(): AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())

async def book_nobs(subject: str, plan_first: bool, outdir: str|None, max_chunks: int|None, window: int|None):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(os.path.join(outdir or BOOKS_DIR, f"{slug}.nobs.md"))
    outline_path = os.path.join(outdir or BOOKS_DIR, f"{slug}.nobs.outline.md")
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    sys_text = repo_render("book.nobs", subject=subject)
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_text = sys_text.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    set_system(sys_text)
    if window is not None: set_window(window)
    if plan_first:
        plan = "Draft a compact outline of the essentials. Only sections that change decisions or understanding. End with NEXT: [Begin]."
        plan_reply = await send_and_collect(build_payload(plan))
        write_to_file(outline_path, plan_reply.strip()); ok(f"Saved outline → {outline_path}")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path; AUTO_ON=True; AUTO_COUNT=0; LAST_NEXT_HINT=None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"No‑bullshit autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done(): AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())

# NEW: Bilingual book function
async def book_bilingual(subject: str, lang: str, plan_first: bool, outdir: str|None, max_chunks: int|None, window: int|None):
    ensure_dir(outdir or BOOKS_DIR)
    slug = slugify(subject)
    out_path = next_available_path(os.path.join(outdir or BOOKS_DIR, f"{slug}.bilingual.md"))
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
        write_to_file(outline_path, plan_reply.strip()); ok(f"Saved outline → {outline_path}")
    global AUTO_OUT, AUTO_ON, AUTO_TASK, AUTO_COUNT, LAST_NEXT_HINT, AUTO_MAX
    AUTO_OUT = out_path; AUTO_ON=True; AUTO_COUNT=0; LAST_NEXT_HINT=None
    AUTO_MAX = None if max_chunks in (None, 0) else int(max_chunks)
    ok(f"Bilingual book autopilot ON → {out_path}")
    if AUTO_TASK and not AUTO_TASK.done(): AUTO_TASK.cancel()
    AUTO_TASK = asyncio.create_task(autorun_loop())

# NEW: Bilingual transform function
async def bilingual_transform_file(path: str, lang: str, outdir=None, chunk_kb=45):
    with open(path, "r", encoding="utf-8") as f: text = f.read()
    outdir = outdir or BOOKS_DIR
    ensure_dir(outdir)
    base = slugify(os.path.splitext(os.path.basename(path))[0])
    out_path = next_available_path(os.path.join(outdir, f"{base}.bilingual.md"))
    
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
    set_system(repo_render("bilingual.transform", lang=lang))
    set_window(0)
    
    try:
        parts = chunks_by_bytes(text, max(10_000, chunk_kb*1024))
        for i, chunk in enumerate(parts, 1):
            reply = await send_and_collect(build_payload(chunk), silent=True)
            write_to_file(out_path, reply.strip())
            print(f"[{now()}] Bilingual transform {i}/{len(parts)}")
        ok(f"Bilingual transform → {out_path}")
    finally:
        set_system(SAVE_SYSTEM_STACK.pop())
        set_window(40)

# NEW: Policy generator function
async def policy_from_regulations(reg_file: str, out_dir: str, org=None, jurisdiction=None, chunk_kb=45, synth_chars=16000):
    ensure_dir(out_dir)
    with open(reg_file, "r", encoding="utf-8") as f: reg_text = f.read()
    
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
async def flashcards_from_synth(synth_path: str, out_path: str, n: int = 200, mode: str = "anki"):
    synth = open(synth_path, "r", encoding="utf-8").read()
    fmt = 'Q: ...\nA: ...\n---' if mode=='anki' else '- Question: ...\n  Answer: ...'
    prompt = (
        f"From this synthesis, generate {n} high-quality study cards.\n"
        f"Format: {fmt}\n"
        "Focus on decisions, definitions, formulas, and pitfalls.\n"
        "SYNTHESIS:\n<<<S\n" + synth + "\nS>>>"
    )
    reply = await send_and_collect(build_payload(prompt))
    write_to_file(out_path, reply.strip()); ok(f"Flashcards → {out_path}")

async def glossary_from_synth(synth_path: str, out_path: str):
    synth = open(synth_path, "r", encoding="utf-8").read()
    prompt = "Extract a glossary of terms (A–Z) with tight definitions and a one-line why-it-matters.\nSYNTHESIS:\n<<<S\n"+synth+"\nS>>>"
    reply = await send_and_collect(build_payload(prompt))
    write_to_file(out_path, reply.strip()); ok(f"Glossary → {out_path}")

async def index_from_synth(synth_path: str, out_path: str):
    synth = open(synth_path, "r", encoding="utf-8").read()
    prompt = "Create an index-like map of topics/subtopics for quick lookup. Group related items.\nSYNTHESIS:\n<<<S\n"+synth+"\nS>>>"
    reply = await send_and_collect(build_payload(prompt))
    write_to_file(out_path, reply.strip()); ok(f"Index → {out_path}")

async def answer_chad(question: str, depth: str = "short", bullets: bool = True, refs: bool = True, contra: bool = True):
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
    refs_instr = "Name canonical sources lightly in-text." if refs else "Do not name sources."
    contra_instr = "Briefly steelman main opposing view, then decide." if contra else "Skip opposing view."

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
    SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT); set_system(tpl); set_window(0)
    try:
        text = open(path, "r", encoding="utf-8").read()
        parts = chunks_by_bytes(text, max(10_000, chunk_kb*1024))
        base = os.path.splitext(os.path.basename(path))[0]
        out_path = next_available_path(os.path.join(BOOKS_DIR, f"{slugify(base)}-{slugify(lang)}.md"))
        for i, chunk in enumerate(parts, 1):
            reply = await send_and_collect(build_payload(chunk), silent=True)
            write_to_file(out_path, reply.strip())
            print(f"[{now()}] Translated {i}/{len(parts)}")
        ok(f"Translated file → {out_path}")
    finally:
        set_system(SAVE_SYSTEM_STACK.pop()); set_window(40)

# ---------------- Lossless pipeline ----------------
async def rewrite_lossless(synth_path: str, out_path: str | None = None):
    base = slugify(os.path.splitext(os.path.basename(synth_path))[0])
    if out_path is None:
        out_path = next_available_path(os.path.join(BOOKS_DIR, f"{base}.lossless.md"))
    sys_template = PROMPT_REPO["book.lossless.rewrite"]["system"]
    if OUTPUT_BUDGET_SNIPPET_ON:
        sys_template = sys_template.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM
    await rewrite_start(synth_path, out_path, system_template=sys_template)

async def lossless_run(path: str, outdir: str|None = None, chunk_kb: int = 45, synth_chars: int = 12000):
    outdir = outdir or BOOKS_DIR; ensure_dir(outdir)
    base = slugify(os.path.splitext(os.path.basename(path))[0])
    synth_path = os.path.join(outdir, f"{base}.lossless.synth.md")
    await ingest_synth_loop(path, synth_path, chunk_kb, synth_chars)
    await rewrite_lossless(synth_path, os.path.join(outdir, f"{base}.lossless.md"))

# ---------------- Helpers to tweak runtime ----------------
def set_system(text: str):
    global SYSTEM_PROMPT; SYSTEM_PROMPT = text or ""

def set_window(n: int):
    global HISTORY_WINDOW; HISTORY_WINDOW = max(0, int(n))

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
    print("Prompt repo:")
    print("  /repo.list")
    print("  /repo.show <key> [n]")
    print("  /repo.use <key> [args]      (advanced)")
    print("Books (subject-aware):")
    print("  /book.zero2hero <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]")
    print("  /book.reference <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]")
    print("  /book.nobs <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]")
    print("  /book.pop <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]")
    print("  /book.bilingual <subject> --lang=LANG [--plan] [--max=N] [--window=N] [--outdir=DIR]")
    print("  /exam.cram <subject> [--max=N] [--window=N] [--outdir=DIR]")
    print("Autopilot control:")
    print("  /book.pause | /book.resume | /next <text>   (one-shot override for the next prompt)")
    print("  /book.hammer on|off               Toggle strict no-wrap continuation hint for self-study")
    print("Output budget:")
    print("  /out.budget on|off                 Append OUTPUT BUDGET addendum to book prompts (default on)")
    print("  /out.push on|off                   Auto-extend within a subtopic to hit min length (default on)")
    print("  /out.minchars <N>                  Set minimal chars per chunk before moving on (default 4500)")
    print("  /out.passes <N>                    Max extension steps per chunk (default 3)")
    print("  /cf.status                        Show Cloudflare status")
    print("  /cf.resume                        Clear CF pause after you solved the challenge")
    print("  /cf.reset                         Force-clear CF flags (debug)")
    print("  /cont.mode [normal|anchor]        Set continuation strategy (default: anchor)")
    print("  /cont.anchor <N>                  Set anchor length in chars (default 200)")
    print("  /repeat.warn on|off               Toggle repetition warning (default on)")
    print("  /repeat.thresh <0..1>            Set repetition Jaccard threshold (default 0.35)")
    print("  /debug.cont                       Show current anchor and LAST NEXT hint")
    print("  /debug.ctx                        Show how many messages are in context window")
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
    print("  /policy.from <reg_file> <out_dir> [--org='...'] [--jurisdiction='...'] [--chunkKB=45] [--synthChars=16000]")
    print("Study/Translate:")
    print("  /flashcards.from <synth.md> <out.md> [n=200]")
    print("  /glossary.from <synth.md> <out.md>")
    print("  /index.from <synth.md> <out.md>")
    print("  /translate.file <file> <language> [chunkKB=50]")
    print("Q&A:")
    print('  /chad "<question>" [--depth=short|medium|deep] [--prose] [--norefs] [--nocontra]')
    print("Prompt & Model:")
    print("  /system <line> | /systemfile <path> | /system.append (paste, end with EOF)")
    print("  /style.nobs on|off                  Harden language (plain, no fluff) for current session")
    print("  /model <uuid|none> | /window <N> | /history.tail | /mono | /clear | /exit")
    print("OpenRouter:")
    print("  /backend bridge|openrouter          Switch backend")
    print("  /or.model <model>                  Set OpenRouter model")
    print("  /or.status                         Show OpenRouter status")
    print("  /or.ref <url>                      Set HTTP-Referer (optional)")
    print("  /or.title <text>                   Set X-Title (optional)")
    print(hr())

def show_status():
    info("Status:")
    print(f"  Browser polling: {'yes' if CLIENT_SEEN else 'no'}")
    print(f"  IDs: session={SESSION_ID or '-'} message={MESSAGE_ID or '-'}")
    print(f"  Model: {MODEL_ID or '(session default)'}   History window: {HISTORY_WINDOW}")
    print(f"  System directive set: {'yes' if SYSTEM_PROMPT.strip() else 'no'}")
    print(f"  Ingest: {'ON' if ING_ON else 'OFF'} mode={ING_MODE or '-'} pos={ING_POS}/{ING_TOTAL} file={os.path.basename(ING_PATH) if ING_PATH else '-'}  synth_out={SYNTH_OUT or '-'}")
    print(f"  Autopilot: {'ON' if AUTO_ON else 'OFF'} paused={AUTO_PAUSE} chunks={AUTO_COUNT} next={LAST_NEXT_HINT or '-'} out={AUTO_OUT or '-'}")

def prompt(): print(f"{C.INFO}> {C.R}", end="", flush=True)

async def read_multiline(hint="Paste lines. End with: EOF"):
    print(hint)
    buf=[]; loop=asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line: break
        if line.strip()=="EOF": break
        buf.append(line.rstrip("\n"))
    return "\n".join(buf)

async def repl():
    global CAPTURE_FLAG, SESSION_ID, MESSAGE_ID, SYSTEM_PROMPT, MODEL_ID
    global AUTO_ON, AUTO_TASK, AUTO_OUT, AUTO_MAX, AUTO_COUNT, LAST_NEXT_HINT, NEXT_OVERRIDE, AUTO_PAUSE
    global ING_ON, ING_TASK, ING_MODE, ING_PATH, ING_POS, ING_TOTAL, ING_CHUNK_BYTES, SYNTH_LIMIT, SYNTH_OUT
    global BACKEND, OR_MODEL, OR_REFERRER, OR_TITLE

    help_text(); prompt()
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line: break
        line = line.rstrip("\n")
        if not line.strip():
            prompt(); continue

        if line.startswith("/"):
            parts = line.split(" ", 2); cmd = parts[0].lower()

            # Core
            if cmd == "/help": help_text()
            elif cmd == "/exit": print("Bye."); raise SystemExit(0)
            elif cmd == "/status": show_status()
            elif cmd == "/capture": CAPTURE_FLAG=True; ok("Capture ON. Click Retry in LMArena.")
            elif cmd == "/setids" and len(parts)>=3: SESSION_ID, MESSAGE_ID=parts[1], parts[2]; ok("IDs set.")
            elif cmd == "/showids": print(f"session_id={SESSION_ID or '(unset)'}\nmessage_id={MESSAGE_ID or '(unset)'}")

            # Repo
            elif cmd == "/repo.list":
                print(repo_list())
            elif cmd == "/repo.show":
                toks = line.split()
                if len(toks) < 2: err("Usage: /repo.show <key> [n]")
                else:
                    key=toks[1]
                    if key not in PROMPT_REPO: err("Unknown key.")
                    else:
                        n=int(toks[2]) if len(toks)>=3 and toks[2].isdigit() else 500
                        text = PROMPT_REPO[key]["system"]
                        print((text[:n] + ("..." if len(text)>n else "")))
            elif cmd == "/repo.use":
                toks=line.split()
                if len(toks)<2: err("Usage: /repo.use <key> [args]"); prompt(); continue
                key=toks[1]
                if key not in PROMPT_REPO: err("Unknown repo key."); prompt(); continue
                if key=="translate":
                    if len(toks)<3: err("Usage: /repo.use translate <lang>"); prompt(); continue
                    set_system(repo_render("translate", lang=" ".join(toks[2:])))
                    ok("Translator system set.")
                elif key=="brainstorm":
                    set_system(repo_render("brainstorm"))
                    ok("Brainstorm system set.")
                elif key in ("book.zero2hero","book.reference","book.pop","exam.cram","book.bilingual"):
                    if len(toks)<3: err(f"Usage: /repo.use {key} <subject>"); prompt(); continue
                    if key == "book.bilingual":
                        # Special case for bilingual - needs lang
                        subject = toks[2]
                        lang = None
                        for tk in toks[3:]:
                            if tk.startswith("--lang="):
                                lang = tk.split("=",1)[1]
                                break
                        if not lang:
                            err("For /repo.use book.bilingual, provide --lang=LANG")
                            prompt(); continue
                        set_system(repo_render(key, subject=subject, lang=lang))
                    else:
                        set_system(repo_render(key, subject=" ".join(toks[2:])))
                    ok(f"{key} system set.")
                elif key=="book.lossless.rewrite":
                    set_system(PROMPT_REPO[key]["system"]); ok("Lossless rewrite system set.")
                else:
                    set_system(PROMPT_REPO[key]["system"]); ok(f"{key} system set.")

            # Subject-aware book modes
            elif cmd == "/book.zero2hero":
                if len(parts) < 2:
                    err("Usage: /book.zero2hero <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"); prompt(); continue
                tokens = line.split()[1:]
                subject_tokens=[]; plan=False; maxc=None; wind=None; outdir=None
                for tk in tokens:
                    if tk=="--plan": plan=True
                    elif tk.startswith("--max="):
                        try: maxc=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--window="):
                        try: wind=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--outdir="): outdir=tk.split("=",1)[1]
                    elif tk.startswith("--"): pass
                    else: subject_tokens.append(tk)
                if not subject_tokens:
                    err("Provide a subject, e.g., /book.zero2hero Psychology"); prompt(); continue
                await book_zero2hero(" ".join(subject_tokens), plan, outdir, maxc, wind)

            elif cmd == "/book.reference":
                if len(parts) < 2:
                    err("Usage: /book.reference <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"); prompt(); continue
                tokens = line.split()[1:]
                subject_tokens=[]; plan=False; maxc=None; wind=None; outdir=None
                for tk in tokens:
                    if tk=="--plan": plan=True
                    elif tk.startswith("--max="):
                        try: maxc=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--window="):
                        try: wind=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--outdir="): outdir=tk.split("=",1)[1]
                    elif tk.startswith("--"): pass
                    else: subject_tokens.append(tk)
                if not subject_tokens: err("Provide a subject."); prompt(); continue
                await book_reference(" ".join(subject_tokens), plan, outdir, maxc, wind)

            elif cmd == "/book.pop":
                if len(parts) < 2:
                    err("Usage: /book.pop <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"); prompt(); continue
                tokens = line.split()[1:]
                subject_tokens=[]; plan=False; maxc=None; wind=None; outdir=None
                for tk in tokens:
                    if tk=="--plan": plan=True
                    elif tk.startswith("--max="):
                        try: maxc=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--window="):
                        try: wind=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--outdir="): outdir=tk.split("=",1)[1]
                    elif tk.startswith("--"): pass
                    else: subject_tokens.append(tk)
                if not subject_tokens: err("Provide a subject."); prompt(); continue
                await book_pop(" ".join(subject_tokens), plan, outdir, maxc, wind)

            elif cmd == "/book.nobs":
                if len(parts) < 2:
                    err("Usage: /book.nobs <subject> [--plan] [--max=N] [--window=N] [--outdir=DIR]"); prompt(); continue
                tokens = line.split()[1:]
                subject_tokens=[]; plan=False; maxc=None; wind=None; outdir=None
                for tk in tokens:
                    if tk=="--plan": plan=True
                    elif tk.startswith("--max="):
                        try: maxc=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--window="):
                        try: wind=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--outdir="): outdir=tk.split("=",1)[1]
                    elif tk.startswith("--"): pass
                    else: subject_tokens.append(tk)
                if not subject_tokens: err("Provide a subject."); prompt(); continue
                await book_nobs(" ".join(subject_tokens), plan, outdir, maxc, wind)

            elif cmd == "/book.bilingual":
                # /book.bilingual <subject> --lang=LANG [--plan] [--max=N] [--window=N] [--outdir=DIR]
                tokens = line.split()[1:]
                subject_tokens=[]; plan=False; maxc=None; wind=None; outdir=None; lang=None
                for tk in tokens:
                    if tk=="--plan": plan=True
                    elif tk.startswith("--lang="): lang=tk.split("=",1)[1]
                    elif tk.startswith("--max="): maxc=int(tk.split("=",1)[1])
                    elif tk.startswith("--window="): wind=int(tk.split("=",1)[1])
                    elif tk.startswith("--outdir="): outdir=tk.split("=",1)[1]
                    elif tk.startswith("--"): pass
                    else: subject_tokens.append(tk)
                if not subject_tokens or not lang:
                    err("Usage: /book.bilingual <subject> --lang=LANG [--plan] [--max=N] [--window=N] [--outdir=DIR]")
                else:
                    await book_bilingual(" ".join(subject_tokens), lang, plan, outdir, maxc, wind)

            elif cmd == "/exam.cram":
                if len(parts) < 2:
                    err("Usage: /exam.cram <subject> [--max=N] [--window=N] [--outdir=DIR]"); prompt(); continue
                tokens = line.split()[1:]
                subject_tokens=[]; maxc=None; wind=None; outdir=None
                for tk in tokens:
                    if tk.startswith("--max="):
                        try: maxc=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--window="):
                        try: wind=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--outdir="): outdir=tk.split("=",1)[1]
                    elif tk.startswith("--"): pass
                    else: subject_tokens.append(tk)
                if not subject_tokens: err("Provide a subject."); prompt(); continue
                await exam_cram(" ".join(subject_tokens), outdir, maxc, wind)

            # Autopilot control
            elif cmd == "/book.pause":
                AUTO_PAUSE = True; ok("Autopilot paused. Use /book.resume or /next to override next prompt.")
            elif cmd == "/book.resume":
                AUTO_PAUSE = False; ok("Autopilot resumed.")
            elif cmd == "/next":
                if len(parts) < 2:
                    err('Usage: /next <text>. Example: /next Continue up to master\'s level; do not end after basics.')
                else:
                    NEXT_OVERRIDE = parts[1]
                    ok(f"Next prompt override set: {NEXT_OVERRIDE!r}")

            elif cmd == "/book.hammer":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on","off"):
                    COVERAGE_HAMMER_ON = (parts[1].strip().lower() == "on")
                    ok(f"Self-study continuation hammer: {COVERAGE_HAMMER_ON}")
                else:
                    err("Usage: /book.hammer on|off")

            elif cmd == "/out.budget":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on","off"):
                    OUTPUT_BUDGET_SNIPPET_ON = (parts[1].strip().lower() == "on")
                    ok(f"OUTPUT_BUDGET addendum: {OUTPUT_BUDGET_SNIPPET_ON}")
                else:
                    err("Usage: /out.budget on|off")

            elif cmd == "/out.push":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on","off"):
                    OUTPUT_PUSH_ON = (parts[1].strip().lower() == "on")
                    ok(f"Output push: {OUTPUT_PUSH_ON}")
                else:
                    err("Usage: /out.push on|off")

            elif cmd == "/out.minchars":
                if len(parts) >= 2:
                    try:
                        v = int(parts[1]); 
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
                        v = int(parts[1]); 
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
                ok("Cloudflare cleared. Now run /book.resume to continue generation (or keep it paused to /next steer).")

            elif cmd == "/cf.reset":
                # hard reset flags; won't auto-resume
                CF_BLOCKED = False
                CF_NOTIFIED = False
                ok("CF flags reset.")

            # Prompt & Model
            elif cmd == "/system":
                SYSTEM_PROMPT = parts[1] if len(parts)>=2 else ""
                ok("System set." if SYSTEM_PROMPT else "System cleared.")
            elif cmd == "/systemfile" and len(parts)>=2:
                try:
                    with open(parts[1], "r", encoding="utf-8") as f: SYSTEM_PROMPT = f.read()
                    ok(f"Loaded system from {parts[1]}")
                except Exception as e: err(f"Failed: {e}")
            elif cmd == "/system.append":
                add = await read_multiline()
                if add.strip():
                    SYSTEM_PROMPT = (SYSTEM_PROMPT + ("\n\n" if SYSTEM_PROMPT.strip() else "") + add).strip()
                    ok("System appended.")
                else: warn("Nothing pasted.")
            elif cmd == "/model":
                if len(parts)>=2:
                    arg = parts[1].strip().lower()
                    if arg=="none": MODEL_ID=None; ok("Model cleared.")
                    else: MODEL_ID=parts[1].strip(); ok(f"Model={MODEL_ID}")
                else: print(f"Current model: {MODEL_ID or '(session default)'}")
            elif cmd == "/window" and len(parts)>=2:
                try: set_window(int(parts[1])); ok(f"Window={HISTORY_WINDOW}")
                except: err("Provide an integer.")

            # OpenRouter commands
            elif cmd == "/backend":
                if len(parts) >= 2 and parts[1].strip().lower() in ("bridge","openrouter"):
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
            elif cmd == "/ingest.ack" and len(parts)>=2:
                path = parts[1]; chunk_kb=80
                if len(parts)==3:
                    try: chunk_kb=max(8,int(parts[2]))
                    except: pass
                if ING_TASK and not ING_TASK.done(): warn("Ingestion already running."); prompt(); continue
                ING_TASK = asyncio.create_task(ingest_ack_loop(path, chunk_kb))
                ok(f"Started ACK ingestion from {path}")
            elif cmd == "/ingest.synth":
                toks = line.split()
                if len(toks) < 3:
                    err("Usage: /ingest.synth <file> <synth.md> [chunkKB=45] [synthChars=9500]")
                else:
                    path=toks[1]; out=toks[2]
                    chunk_kb=int(toks[3]) if len(toks)>=4 and toks[3].isdigit() else 45
                    synth_chars=int(toks[4]) if len(toks)>=5 and toks[4].isdigit() else 9500
                    if ING_TASK and not ING_TASK.done(): warn("Ingestion already running."); prompt(); continue
                    ING_TASK = asyncio.create_task(ingest_synth_loop(path, out, chunk_kb, synth_chars))
                    ok(f"Started SYNTH ingestion from {path} → {out}")
            elif cmd == "/ingest.lossless":
                toks = line.split()
                if len(toks) < 3:
                    err("Usage: /ingest.lossless <file> <synth.md> [chunkKB=45] [synthChars=12000]")
                else:
                    path=toks[1]; out=toks[2]
                    chunk_kb=int(toks[3]) if len(toks)>=4 and toks[3].isdigit() else 45
                    synth_chars=int(toks[4]) if len(toks)>=5 and toks[4].isdigit() else 12000
                    if ING_TASK and not ING_TASK.done(): warn("Ingestion already running."); prompt(); continue
                    ING_TASK = asyncio.create_task(ingest_synth_loop(path, out, chunk_kb, synth_chars))
                    ok(f"Started LOSSLESS synthesis from {path} → {out}")
            elif cmd == "/ingest.stop":
                if ING_ON: ING_ON=False; ok("Stopping ingestion…")
                else: warn("No ingestion running.")
            elif cmd == "/ingest.status":
                show_status()
            elif cmd == "/style.capture":
                toks = line.split()
                if len(toks) < 3: err("Usage: /style.capture <file> <style.synth.md> [chunkKB=30] [styleChars=6000]"); prompt(); continue
                path, out = toks[1], toks[2]
                chunk_kb = int(toks[3]) if len(toks)>=4 and toks[3].isdigit() else 30
                style_chars = int(toks[4]) if len(toks)>=5 and toks[4].isdigit() else 6000
                if ING_TASK and not ING_TASK.done(): warn("Ingestion already running."); prompt(); continue
                ING_TASK = asyncio.create_task(ingest_style_loop(path, out, chunk_kb, style_chars))
                ok(f"Started style capture from {path} → {out}")
            elif cmd == "/style.apply":
                toks = line.split()
                if len(toks) < 3: err("Usage: /style.apply <style.synth.md> <topic|file> [out.md] [--words=N]"); prompt(); continue
                style, topic = toks[1], toks[2]
                out = None; words=None
                for tk in toks[3:]:
                    if tk.startswith("--words="):
                        try: words=int(tk.split("=",1)[1])
                        except: pass
                    else:
                        out=tk
                await style_apply(style, topic, out, words=None if not words else int(words))

            elif cmd == "/style.nobs":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on","off"):
                    val = parts[1].strip().lower()
                    global NO_BS_ACTIVE
                    if val == "on" and not NO_BS_ACTIVE:
                        SAVE_SYSTEM_STACK.append(SYSTEM_PROMPT)
                        set_system(SYSTEM_PROMPT.strip() + "\n\n" + NO_BS_ADDENDUM)
                        NO_BS_ACTIVE = True; ok("No‑bullshit language ON (session).")
                    elif val == "off" and NO_BS_ACTIVE:
                        if SAVE_SYSTEM_STACK:
                            set_system(SAVE_SYSTEM_STACK.pop())
                        NO_BS_ACTIVE = False; ok("No‑bullshit language OFF.")
                    else:
                        warn("Already in desired state.")
                else:
                    err("Usage: /style.nobs on|off")

            # Rewrite/Lossless
            elif cmd == "/rewrite.start":
                toks = line.split()
                if len(toks) < 3: err("Usage: /rewrite.start <synth.md> <out.md>")
                else: await rewrite_start(toks[1], toks[2])
            elif cmd == "/rewrite.lossless":
                toks = line.split()
                if len(toks) < 2: err("Usage: /rewrite.lossless <synth.md> [out.md]")
                else:
                    synth = toks[1]; out = toks[2] if len(toks)>=3 else None
                    await rewrite_lossless(synth, out)

            # One-shot lossless pipeline
            elif cmd == "/lossless.run":
                toks = line.split()
                if len(toks) < 2: err("Usage: /lossless.run <file> [--outdir=DIR] [--chunkKB=45] [--synthChars=12000]"); prompt(); continue
                path = toks[1]; outdir=None; ck=45; sc=12000
                for tk in toks[2:]:
                    if tk.startswith("--outdir="): outdir=tk.split("=",1)[1]
                    elif tk.startswith("--chunkKB="):
                        try: ck=int(tk.split("=",1)[1])
                        except: pass
                    elif tk.startswith("--synthChars="):
                        try: sc=int(tk.split("=",1)[1])
                        except: pass
                await lossless_run(path, outdir, chunk_kb=ck, synth_chars=sc)

            # NEW: Bilingual and Policy commands
            elif cmd == "/bilingual.file":
                # /bilingual.file <file> --lang=LANG [--outdir=DIR] [--chunkKB=45]
                toks=line.split()
                if len(toks) < 2: err("Usage: /bilingual.file <file> --lang=LANG [--outdir=DIR] [--chunkKB=45]")
                else:
                    path=toks[1]; lang=None; outdir=None; ck=45
                    for tk in toks[2:]:
                        if tk.startswith("--lang="): lang=tk.split("=",1)[1]
                        elif tk.startswith("--outdir="): outdir=tk.split("=",1)[1]
                        elif tk.startswith("--chunkKB="): ck=int(tk.split("=",1)[1])
                    if not lang: err("Provide --lang=LANG")
                    else: await bilingual_transform_file(path, lang, outdir, chunk_kb=ck)

            elif cmd == "/policy.from":
                # /policy.from <reg_file> <out_dir> [--org="..."] [--jurisdiction="..."] [--chunkKB=45] [--synthChars=16000]
                toks=line.split()
                if len(toks) < 3: err('Usage: /policy.from <reg_file> <out_dir> [--org="..."] [--jurisdiction="..."] [--chunkKB=45] [--synthChars=16000]')
                else:
                    reg=toks[1]; outd=toks[2]; org=None; juris=None; ck=45; sc=16000
                    for tk in toks[3:]:
                        if tk.startswith("--org="): org=tk.split("=",1)[1].strip('"')
                        elif tk.startswith("--jurisdiction="): juris=tk.split("=",1)[1].strip('"')
                        elif tk.startswith("--chunkKB="): ck=int(tk.split("=",1)[1])
                        elif tk.startswith("--synthChars="): sc=int(tk.split("=",1)[1])
                    await policy_from_regulations(reg, outd, org=org, jurisdiction=juris, chunk_kb=ck, synth_chars=sc)

            # Study/Translate
            elif cmd == "/flashcards.from":
                toks = line.split()
                if len(toks) < 3: err("Usage: /flashcards.from <synth.md> <out.md> [n=200]"); prompt(); continue
                n = int(toks[3]) if len(toks)>=4 and toks[3].isdigit() else 200
                await flashcards_from_synth(toks[1], toks[2], n=n)
            elif cmd == "/glossary.from":
                toks = line.split()
                if len(toks) < 3: err("Usage: /glossary.from <synth.md> <out.md>"); prompt(); continue
                await glossary_from_synth(toks[1], toks[2])
            elif cmd == "/index.from":
                toks = line.split()
                if len(toks) < 3: err("Usage: /index.from <synth.md> <out.md>"); prompt(); continue
                await index_from_synth(toks[1], toks[2])
            elif cmd == "/translate.file":
                toks = line.split()
                if len(toks) < 3: err("Usage: /translate.file <file> <language> [chunkKB=50]"); prompt(); continue
                chunk_kb = int(toks[3]) if len(toks)>=4 and toks[3].isdigit() else 50
                await translate_file(toks[1], " ".join(toks[2:3]), chunk_kb=chunk_kb)
            elif cmd == "/chad":
                # /chad "What is X?" [--depth=short|medium|deep] [--prose] [--norefs] [--nocontra]
                m = re.findall(r'"([^"]+)"', line)
                if not m:
                    err('Usage: /chad "your question" [--depth=short|medium|deep] [--prose] [--norefs] [--nocontra]')
                    prompt(); continue
                q = m[0]
                depth = "short"; bullets = True; refs = True; contra = True
                for tk in line.split():
                    if tk.startswith("--depth="):
                        depth = tk.split("=",1)[1].strip().lower()
                    elif tk == "--prose":
                        bullets = False
                    elif tk == "--norefs":
                        refs = False
                    elif tk == "--nocontra":
                        contra = False
                await answer_chad(q, depth=depth, bullets=bullets, refs=refs, contra=contra)
                prompt(); continue

            # Manual autopilot
            elif cmd == "/book.start" and len(parts)>=2:
                AUTO_OUT = parts[1]; AUTO_ON=True; AUTO_COUNT=0; LAST_NEXT_HINT=None
                ok(f"Autopilot ON → {AUTO_OUT}")
                if AUTO_TASK and not AUTO_TASK.done(): AUTO_TASK.cancel()
                AUTO_TASK = asyncio.create_task(autorun_loop())
            elif cmd == "/book.stop":
                AUTO_ON=False; ok("Autopilot OFF.")
            elif cmd == "/book.max" and len(parts)>=2:
                try:
                    n=int(parts[1]); AUTO_MAX=None if n<=0 else n; ok(f"Auto max={AUTO_MAX or '(unlimited)'}")
                except: err("Provide an integer.")
            elif cmd == "/book.status":
                show_status()

            # Misc
            elif cmd == "/mono":
                global USE_COLOR
                USE_COLOR = not USE_COLOR; _apply_colors(); ok(f"Monochrome {'ON' if not USE_COLOR else 'OFF'}.")
            elif cmd == "/clear":
                HISTORY.clear(); ok("History cleared.")
            elif cmd == "/history.tail":
                try:
                    u = next((m for m in reversed(HISTORY) if m["role"] == "user"), None)
                    a = next((m for m in reversed(HISTORY) if m["role"] == "assistant"), None)
                    print(hr())
                    if u:
                        print(f"Last user: {u['content'][:500] + ('...' if len(u['content'])>500 else '')}")
                    if a:
                        print(f"Last assistant: {a['content'][:500] + ('...' if len(a['content'])>500 else '')}")
                    print(hr())
                except Exception as e:
                    err(f"history.tail failed: {e}")
            elif cmd == "/cont.mode":
                if len(parts) >= 2 and parts[1].strip().lower() in ("normal","anchor"):
                    CONT_MODE = parts[1].strip().lower()
                    ok(f"Continuation mode: {CONT_MODE}")
                else:
                    err("Usage: /cont.mode [normal|anchor]")

            elif cmd == "/cont.anchor":
                if len(parts) >= 2:
                    try:
                        n = int(parts[1]); 
                        if n < 50 or n > 2000:
                            warn("Choose a value between 50 and 2000.")
                        else:
                            CONT_ANCHOR_CHARS = n; ok(f"Anchor length: {CONT_ANCHOR_CHARS}")
                    except:
                        err("Provide an integer.")
                else:
                    err("Usage: /cont.anchor <N>")

            elif cmd == "/repeat.warn":
                if len(parts) >= 2 and parts[1].strip().lower() in ("on","off"):
                    REPEAT_WARN = (parts[1].strip().lower()=="on"); ok(f"Repeat warn: {REPEAT_WARN}")
                else:
                    err("Usage: /repeat.warn on|off")

            elif cmd == "/repeat.thresh":
                if len(parts) >= 2:
                    try:
                        t = float(parts[1]); 
                        if t <= 0 or t >= 1: warn("Use a value between 0 and 1 (e.g., 0.35).")
                        else:
                            REPEAT_THRESH = t; ok(f"Repeat threshold: {REPEAT_THRESH}")
                    except:
                        err("Provide a float (0..1).")
                else:
                    err("Usage: /repeat.thresh <0..1>")

            elif cmd == "/debug.cont":
                anch = continuation_anchor(CONT_ANCHOR_CHARS)
                print(hr()); 
                print(f"Anchor ({len(anch)} chars): {anch!r}")
                print(f"LAST_NEXT_HINT: {LAST_NEXT_HINT!r}")
                print(hr())

            elif cmd == "/debug.ctx":
                ctx = trimmed_history()
                print(hr())
                print(f"Context messages included: {len(ctx)}")
                if ctx:
                    print(f"First in ctx: {ctx[0]['role']} … Last in ctx: {ctx[-1]['role']}")
                print(hr())
            else:
                warn("Unknown command. /help for help.")
            prompt(); continue

        # manual chat
        if AUTO_ON:
            warn("Autopilot running. Use /book.pause and /next to intervene, or /book.stop to stop."); prompt(); continue
        try:
            await ask_collect(line)
        except Exception as e:
            err(f"Error: {e}")
        prompt()

# ---------------- Style apply ----------------
async def style_apply(style_path: str, topic_or_file: str, out_path: str|None, max_words: int|None):
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

# ---------------- App bootstrap ----------------
def main():
    app = web.Application()
    app.router.add_get("/bridge/poll", bridge_poll)
    app.router.add_post("/bridge/push", bridge_push)
    app.router.add_route("OPTIONS", "/bridge/push", lambda r: _add_cors(web.Response(text="")))
    app.router.add_post("/internal/id_capture/update", id_capture_update)
    app.router.add_route("OPTIONS", "/internal/id_capture/update", lambda r: _add_cors(web.Response(text="")))
    app.router.add_get("/internal/healthz", healthz)

    runner = web.AppRunner(app)
    async def _run():
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 5102); await site.start()
        info("Listening on:")
        print("  GET  http://127.0.0.1:5102/bridge/poll")
        print("  POST http://127.0.0.1:5102/bridge/push")
        print("  POST http://127.0.0.1:5102/internal/id_capture/update")
        await repl()

    try: asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit): pass
    finally:
        try:
            loop = asyncio.new_event_loop(); loop.run_until_complete(runner.cleanup()); loop.close()
        except Exception: pass

if __name__ == "__main__":
    main()