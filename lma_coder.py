#!/usr/bin/env python3
# lma_coder.py
# Local coder CLI using the same CSP-safe polling bridge to LMArena.
# Tools: list_dir, read_file, write_file, append_file, run_cmd
# Safety: path-jail to a root dir, confirm runs, size limits, truncation.
# Commands:
#   /capture                -> then click Retry in LMArena (to capture IDs)
#   /setids <sess> <msg>    -> set IDs manually
#   /root <dir>             -> set/editable root (path jail)
#   /confirm on|off         -> toggle confirmation for run_cmd (default: on)
#   /code "<goal>" [--steps=20] [--window=12] [--timeout=180] [--hint="..."] -> start session
#   /pause | /resume | /stop
#   /status
#   /mono | /exit
#
# NOTE: This agent relies on the model following a strict JSON schema. We enforce it via a tool protocol prompt.

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

from aiohttp import web

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings

    PTK_AVAILABLE = True
except Exception:
    PTK_AVAILABLE = False

# --------------- Globals ---------------
ALLOW_CMDS = {
    "ls",
    "dir",
    "echo",
    "cat",
    "type",
    "grep",
    "sed",
    "awk",
    "python",
    "python3",
    "pip",
    "pytest",
    "uvicorn",
    "black",
    "ruff",
    "mypy",
    "git",
}
CANCEL_REQUESTED = False
BACKEND = "polling"  # polling | openai
OPENAI_BASE = "http://127.0.0.1:5102/v1"
OPENAI_API_KEY = ""  # optional

# --------------- Colors/UI ---------------
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


def hr(ch="─"):
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


# --------------- Bridge state ---------------
PENDING_JOBS = []  # [{request_id, payload}]
RESPONSE_CHANNELS = {}  # req_id -> asyncio.Queue
CAPTURE_FLAG = False
CLIENT_SEEN = False

# --------------- Session state ---------------
SESSION_ID = ""
MESSAGE_ID = ""
MODEL_ID = None
HISTORY = []  # [{"role":"user"/"assistant","content":...}]
HISTORY_WINDOW = 12  # steps kept in history for coder mode (compact)

# --------------- Coder config ---------------
ROOT = Path.cwd()  # path jail root
CONFIRM_RUN = True  # confirm for run_cmd
STEP_MAX = 20
STEP_TIMEOUT = 180.0
NEXT_HINT = None  # optional guidance appended to each cycle
RUNNING = False
PAUSED = False

# --------------- Stream parsing ---------------
ERROR_RE = re.compile(r'(\{\s*"error".*?\})', re.DOTALL)
FINISH_RE = re.compile(r'[ab]d:(\{.*?"finishReason".*?\})', re.DOTALL)
CF_PATTERNS = [
    r"<title>Just a moment...</title>",
    r"Enable JavaScript and cookies to continue",
]


def extract_text_chunks(buf: str):
    out = []
    while True:
        m = re.search(r'[ab]0:"', buf)
        if not m:
            break
        start = m.end()
        i = start
        while True:
            j = buf.find('"', i)
            if j == -1:
                return out, buf
            bs = 0
            k = j - 1
            while k >= 0 and buf[k] == "\\":
                bs += 1
                k -= 1
            if bs % 2 == 0:
                esc = buf[start:j]
                try:
                    txt = json.loads('"' + esc + '"')
                    if txt:
                        out.append(txt)
                except Exception:
                    pass
                buf = buf[j + 1 :]
                break
            else:
                i = j + 1
    return out, buf


# --------------- HTTP helpers ---------------
def _add_cors(resp: web.StreamResponse):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Private-Network"] = "true"
    return resp


# --------------- Bridge endpoints (poll/push) ---------------
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


# --------------- ID capture ---------------
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


async def healthz(_req):
    return web.json_response({"status": "ok"})


# --------------- Payload helpers ---------------
def trimmed_history():
    # Keep last HISTORY_WINDOW exchanges (2 messages each)
    n = HISTORY_WINDOW * 2
    return HISTORY[-n:] if len(HISTORY) > n else HISTORY


def build_payload_messages(messages: list[dict]) -> dict:
    # Each message: {"role":"system"/"user"/"assistant","content":str}
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
    global CANCEL_REQUESTED
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
            while True:
                if CANCEL_REQUESTED:
                    if not silent:
                        print(f"\n{C.WARN}[cancelled]{C.R}")
                    RESPONSE_CHANNELS.pop(req_id, None)
                    return "".join(parts)
                try:
                    chunk = await asyncio.wait_for(q.get(), timeout=0.5)
                    break
                except asyncio.TimeoutError:
                    continue
            if isinstance(chunk, dict) and "error" in chunk:
                msg = str(chunk["error"])
                if not silent:
                    print(f"\n{C.ERR}! Error: {msg}{C.R}")
                break
            if chunk == "[DONE]":
                break
            buf += str(chunk)
            for p in CF_PATTERNS:
                if re.search(p, buf, re.IGNORECASE):
                    if not silent:
                        print(
                            f"\n{C.WARN}! Cloudflare challenge. Solve it in browser and retry.{C.R}"
                        )
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
            mf = FINISH_RE.search(buf)
            if mf:
                buf = buf[mf.end() :]
    except asyncio.TimeoutError:
        if not silent:
            print(f"\n{C.WARN}! Step timed out.{C.R}")
    if CANCEL_REQUESTED and not silent:
        print(f"{C.INFO}(note: cancel cleared){C.R}")
    globals()["CANCEL_REQUESTED"] = False
    if not silent:
        print()
    RESPONSE_CHANNELS.pop(req_id, None)
    return "".join(parts)


# --------------- Tool executors ---------------
def resolve_path(p: str) -> Path:
    # path jail under ROOT
    base = ROOT.resolve()
    target = (base / p).resolve()
    if base not in target.parents and target != base:
        raise PermissionError(f"Path escapes root: {p}")
    return target


MAX_IO_BYTES = 80_000
TRUNC_HEAD = 6000
TRUNC_TAIL = 2000


def truncate_text(txt: str, label: str = "output") -> str:
    b = txt.encode("utf-8")
    if len(b) <= MAX_IO_BYTES:
        return txt
    head = b[:TRUNC_HEAD].decode("utf-8", errors="ignore")
    tail = b[-TRUNC_TAIL:].decode("utf-8", errors="ignore")
    return (
        head
        + f"\n\n...[TRUNCATED {len(b)-TRUNC_HEAD-TRUNC_TAIL} bytes of {label}]...\n\n"
        + tail
    )


def tool_list_dir(path: str) -> dict:
    p = resolve_path(path)
    if not p.exists():
        return {"ok": False, "error": "not_found"}
    items = []
    for e in sorted(p.iterdir()):
        try:
            st = e.stat()
            items.append(
                {
                    "name": e.name,
                    "type": "dir" if e.is_dir() else "file",
                    "size": st.st_size,
                }
            )
        except Exception:
            items.append({"name": e.name, "type": "unknown"})
    return {"ok": True, "entries": items}


def tool_read_file(path: str) -> dict:
    p = resolve_path(path)
    if not p.exists():
        return {"ok": False, "error": "not_found"}
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        return {"ok": True, "content": truncate_text(txt, "file")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_write_file(path: str, content: str) -> dict:
    p = resolve_path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_append_file(path: str, content: str) -> dict:
    p = resolve_path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_search_text(
    path: str, query: str, regex: bool = False, max_results: int = 200
) -> dict:
    p = resolve_path(path)
    hits = []
    try:
        if p.is_file():
            files = [p]
        else:
            files = []
            for root, _, names in os.walk(p):
                for n in names:
                    if n.startswith("."):
                        continue
                    fp = Path(root) / n
                    try:
                        if fp.stat().st_size <= 300_000:  # 300KB safety
                            files.append(fp)
                    except Exception:
                        pass
        import re as _re

        pat = _re.compile(query) if regex else None
        for f in files:
            try:
                txt = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(txt.splitlines(), 1):
                if pat.search(line) if regex else (query in line):
                    hits.append(
                        {
                            "file": str(f.relative_to(resolve_path("."))),
                            "line": i,
                            "text": line[:400],
                        }
                    )
                    if len(hits) >= max_results:
                        return {"ok": True, "results": hits, "truncated": True}
        return {"ok": True, "results": hits, "truncated": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_replace_text(
    path: str, find: str, replace: str, regex: bool = False, count: int = 0
) -> dict:
    fp = resolve_path(path)
    if not fp.exists() or not fp.is_file():
        return {"ok": False, "error": "not_found"}
    try:
        import re as _re

        txt = fp.read_text(encoding="utf-8", errors="ignore")
        if regex:
            pat = _re.compile(find, _re.MULTILINE | _re.DOTALL)
            new_txt, n = pat.subn(replace, txt, 0 if count <= 0 else count)
        else:
            if count and count > 0:
                new_txt = txt.replace(find, replace, count)
                n = txt.count(find) if count > txt.count(find) else count
            else:
                n = txt.count(find)
                new_txt = txt.replace(find, replace)
        if new_txt == txt:
            return {"ok": True, "replacements": 0}
        fp.write_text(new_txt, encoding="utf-8")
        return {"ok": True, "replacements": n}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_ask_user(question: str) -> dict:
    print(f"{C.USER}{C.B}Question{C.R}: {question}")
    print("(answer)> ", end="", flush=True)
    try:
        ans = sys.stdin.readline()
    except Exception:
        ans = ""
    return {"ok": True, "answer": ans.strip()}


def confirm(cmd: str) -> bool:
    print(f"{C.WARN}Run?{C.R} {cmd}")
    print("(y/N)> ", end="", flush=True)
    ans = sys.stdin.readline().strip().lower()
    return ans in ("y", "yes")


def tool_apply_patch(path: str, patch: str) -> dict:
    fp = resolve_path(path)
    if not fp.exists() or not fp.is_file():
        return {"ok": False, "error": "not_found"}
    try:
        original = fp.read_text(encoding="utf-8", errors="ignore").splitlines(
            keepends=True
        )
        # parse unified diff into hunks
        lines = patch.splitlines(keepends=False)
        i = 0
        hunks = []
        while i < len(lines):
            if lines[i].startswith(" @@"):
                header = lines[i]
                i += 1
                hunk = []
                while i < len(lines) and not lines[i].startswith(" @@"):
                    if lines[i].startswith(("---", "+++")):
                        break
                    hunk.append(lines[i])
                    i += 1
                hunks.append((header, hunk))
            else:
                i += 1

        def normalize(s):
            return s.rstrip("\r\n")

        def extract_original(hunk):
            return [normalize(l[1:]) for l in hunk if l and l[0] in (" ", "-")]

        def extract_final(hunk):
            # context + additions
            out = []
            for l in hunk:
                if not l:
                    continue
                tag, body = l[0], normalize(l[1:])
                if tag in (" ", "+"):
                    out.append(body + "\n")
            return out

        content = original[:]  # working copy
        applied = 0
        for header, hunk in hunks:
            orig_block = [
                l + ("\n" if not l.endswith("\n") else "")
                for l in extract_original(hunk)
            ]
            final_block = extract_final(hunk)

            # find best match (exact first; then fuzzy by context)
            def match_at(idx):
                for j, ol in enumerate(orig_block):
                    if idx + j >= len(content):
                        return False
                    if normalize(content[idx + j]) != normalize(ol):
                        return False
                return True

            pos = -1
            # try header line numbers first if present
            try:
                # @@ -l,s +l2,s2 @@
                m = re.search(r"-([0-9]+)", header)
                if m:
                    guess = max(0, int(m.group(1)) - 1)
                    if match_at(guess):
                        pos = guess
                # if not, fall through
            except Exception:
                pass
            if pos == -1:
                # scan for exact match
                for k in range(0, max(0, len(content) - len(orig_block) + 1)):
                    if match_at(k):
                        pos = k
                        break
            if pos == -1 and orig_block:
                # fuzzy: slide window and score by context matches
                best = (-1, -1)
                for k in range(0, max(0, len(content) - len(orig_block) + 1)):
                    score = 0
                    for j, ol in enumerate(orig_block):
                        if k + j < len(content) and normalize(
                            content[k + j]
                        ) == normalize(ol):
                            score += 1
                    if score > best[1]:
                        best = (k, score)
                if best[1] > 0:
                    pos = best[0]
            if pos == -1:
                return {"ok": False, "error": f"hunk_not_found: {header}"}
            # replace the span: len(orig_block) lines at pos -> final_block
            content = content[:pos] + final_block + content[pos + len(orig_block) :]
            applied += 1
        fp.write_text("".join(content), encoding="utf-8")
        return {"ok": True, "applied_hunks": applied}
    except Exception as e:
        return {"ok": False, "error": str(e)}


import re as _pytest_re


def _parse_pytest_summary(txt: str) -> dict:
    # Look for "== 3 passed, 1 failed in 0.20s =="
    summary = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "xfailed": 0,
        "xpassed": 0,
        "skipped": 0,
        "warnings": 0,
        "deselected": 0,
        "duration": None,
    }
    m = _pytest_re.search(r"==+ (.+?) ==+", txt)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        for p in parts:
            mm = _pytest_re.search(r"(\d+)\s+(\w+)", p)
            if mm:
                n, key = int(mm.group(1)), mm.group(2).lower()
                if key.startswith("passed"):
                    summary["passed"] = n
                elif key.startswith("failed"):
                    summary["failed"] = n
                elif key.startswith("error"):
                    summary["errors"] = n
                elif key.startswith("xfailed"):
                    summary["xfailed"] = n
                elif key.startswith("xpassed"):
                    summary["xpassed"] = n
                elif key.startswith("skipped"):
                    summary["skipped"] = n
                elif key.startswith("warning"):
                    summary["warnings"] = n
                elif key.startswith("deselected"):
                    summary["deselected"] = n
        d = _pytest_re.search(r"in\s+([0-9.]+)s", m.group(1))
        if d:
            summary["duration"] = float(d.group(1))
    fails = []
    for line in txt.splitlines():
        fm = _pytest_re.match(r"^FAILED\s+(.+?)\s+-\s+", line)
        if fm:
            fails.append(fm.group(1))
    return {"summary": summary, "failures": fails}


def tool_run_tests(args: str = "-q", cwd: str | None = None) -> dict:
    wd = resolve_path(cwd) if cwd else ROOT.resolve()
    try:
        cmd = f"pytest {args}".strip()
        if CONFIRM_RUN:
            if not confirm(f"[cwd={wd}] $ {cmd}"):
                return {"ok": False, "error": "user_denied"}
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(wd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out = proc.stdout or ""
        err = proc.stderr or ""
        report = _parse_pytest_summary(out + "\n" + err)
        return {
            "ok": True,
            "code": proc.returncode,
            "report": report,
            "stdout": truncate_text(out, "stdout"),
            "stderr": truncate_text(err, "stderr"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _to_openai_messages(msgs: list[dict]) -> list[dict]:
    out = []
    for m in msgs:
        role = m.get("role") or "user"
        out.append({"role": role, "content": m.get("content", "")})
    return out


async def send_and_collect_openai(window_messages: list[dict]) -> str:
    url = f"{OPENAI_BASE.rstrip('/')}/chat/completions"
    payload = {
        "model": MODEL_ID or "default",
        "messages": _to_openai_messages(window_messages),
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if OPENAI_API_KEY:
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"
    try:
        import aiohttp
    except Exception:
        print(f"{C.ERR}aiohttp not installed. pip install aiohttp{C.R}")
        return ""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url, json=payload, headers=headers, timeout=STEP_TIMEOUT
            ) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    print(
                        f"{C.ERR}! OpenAI-compatible call failed: {resp.status} {txt[:400]}{C.R}"
                    )
                    return ""
                j = await resp.json()
                return (j.get("choices") or [{}])[0].get("message", {}).get(
                    "content", ""
                ) or ""
        except Exception as e:
            print(f"{C.ERR}! OpenAI-compatible call error: {e}{C.R}")
            return ""


def tool_run_cmd(cmd: str, cwd: str | None = None) -> dict:
    wd = resolve_path(cwd) if cwd else ROOT.resolve()
    try:
        # Enforce allowlist (first word)
        first = (cmd.strip().split() or [""])[0]
        base = os.path.basename(first)
        if base not in ALLOW_CMDS:
            return {"ok": False, "error": f"command_not_allowed: {base}"}
        if CONFIRM_RUN:
            if not confirm(f"[cwd={wd}] $ {cmd}"):
                return {"ok": False, "error": "user_denied"}
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(wd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out = truncate_text(proc.stdout or "", "stdout")
        errt = truncate_text(proc.stderr or "", "stderr")
        return {"ok": True, "code": proc.returncode, "stdout": out, "stderr": errt}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --------------- Tool protocol prompt ---------------
TOOL_SYSTEM = """You are a local coding agent operating via tools. Return ONLY one JSON object per turn.

Schema:
{
  "thought": "brief next-step reasoning (<= 30 words)",
  "plan": ["1) ...", "2) ..."],        // optional; <=4 bullets
  "actions": [
    {"tool":"list_dir","args":{"path":"."}},
    {"tool":"read_file","args":{"path":"..."}},
    {"tool":"write_file","args":{"path":"...","content":"..."}},
    {"tool":"append_file","args":{"path":"...","content":"..."}},
    {"tool":"apply_patch","args":{"path":"...","patch":"<unified diff>"}},
    {"tool":"run_tests","args":{"args":"-q"}},
    {"tool":"run_cmd","args":{"cmd":"pytest -q","cwd":"."}},
    {"tool":"ask_user","args":{"question":"one crisp clarification"}}
  ],
  "final": null
}

Rules:
- Discover before editing: list_dir/read_file the targets you will modify.
- Prefer apply_patch for minimal diffs. Keep changes small and focused.
- Tests: use run_tests (pytest -q) instead of raw run_cmd.
- Keep outputs small (100KB cap). Ask one precise question when blocked.
- Stay inside root. No network ops. Shell only allowlisted commands.
- Stop with "final": "what changed and how to run it" when complete.
"""


# --------------- Coder loop ---------------
async def coder_session(goal: str, steps: int, window: int, hint: str | None):
    global RUNNING, PAUSED, NEXT_HINT
    RUNNING = True
    PAUSED = False
    NEXT_HINT = hint
    messages = []
    sys_prompt = TOOL_SYSTEM.replace("{root}", str(ROOT.resolve()))
    messages.append({"role": "system", "content": sys_prompt})
    messages.append(
        {
            "role": "user",
            "content": f"Goal: {goal}\nConstraints: JSON only. 100KB per message cap.\nBegin.",
        }
    )

    for step in range(1, steps + 1):
        # pause
        while RUNNING and PAUSED:
            await asyncio.sleep(0.2)
        if not RUNNING:
            break

        # send
        window_msgs = messages[-(window * 2 + 2) :]
        print()
        print(f"{C.USER}{C.B}You{C.R}: [coder step {step}]")
        if BACKEND == "openai":
            reply = await send_and_collect_openai(window_msgs)
        else:
            payload = build_payload_messages(window_msgs)
            reply = await send_and_collect(payload)
        if not reply.strip():
            warn("Empty reply; stopping.")
            break

        # parse JSON (first object)
        model_json = None
        try:
            # Try to locate first JSON object
            s = reply
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1 and end > start:
                cand = s[start : end + 1]
                model_json = json.loads(cand)
        except Exception:
            model_json = None

        if not isinstance(model_json, dict) or "actions" not in model_json:
            # ask model to correct
            warn("Non-JSON or bad schema; asking for correction.")
            messages.append({"role": "assistant", "content": reply})
            messages.append(
                {
                    "role": "user",
                    "content": "Your last message was not valid JSON per the schema. Return ONLY the JSON object.",
                }
            )
            continue

        messages.append({"role": "assistant", "content": reply})
        acts = model_json.get("actions", [])
        final_msg = model_json.get("final")

        # execute actions
        observations = []
        for act in acts:
            tool = act.get("tool")
            args = act.get("args", {}) or {}
            try:
                if tool == "list_dir":
                    res = tool_list_dir(args.get("path", "."))
                    observations.append({"tool": tool, "result": res})
                elif tool == "read_file":
                    res = tool_read_file(args.get("path", ""))
                    observations.append({"tool": tool, "result": res})
                elif tool == "write_file":
                    res = tool_write_file(args.get("path", ""), args.get("content", ""))
                    observations.append({"tool": tool, "result": res})
                elif tool == "append_file":
                    res = tool_append_file(
                        args.get("path", ""), args.get("content", "")
                    )
                    observations.append({"tool": tool, "result": res})
                elif tool == "search_text":
                    res = tool_search_text(
                        args.get("path", "."),
                        args.get("query", ""),
                        bool(args.get("regex", False)),
                        int(args.get("max_results", 200)),
                    )
                    observations.append({"tool": tool, "result": res})
                elif tool == "replace_text":
                    res = tool_replace_text(
                        args.get("path", ""),
                        args.get("find", ""),
                        args.get("replace", ""),
                        bool(args.get("regex", False)),
                        int(args.get("count", 0)),
                    )
                    observations.append({"tool": tool, "result": res})
                elif tool == "ask_user":
                    res = tool_ask_user(args.get("question", "Clarify?"))
                    observations.append({"tool": tool, "result": res})
                elif tool == "run_cmd":
                    res = tool_run_cmd(args.get("cmd", ""), args.get("cwd"))
                    observations.append({"tool": tool, "result": res})
                elif tool == "apply_patch":
                    res = tool_apply_patch(args.get("path", ""), args.get("patch", ""))
                    observations.append({"tool": tool, "result": res})
                elif tool == "run_tests":
                    res = tool_run_tests(args.get("args", "-q"), args.get("cwd"))
                    observations.append({"tool": tool, "result": res})
                elif tool == "ask_user":
                    res = tool_ask_user(args.get("question", "Clarify?"))
                    observations.append({"tool": tool, "result": res})
                else:
                    observations.append(
                        {
                            "tool": tool or "unknown",
                            "result": {"ok": False, "error": "unknown_tool"},
                        }
                    )
            except PermissionError as e:
                observations.append(
                    {"tool": tool, "result": {"ok": False, "error": str(e)}}
                )
            except Exception as e:
                observations.append(
                    {"tool": tool, "result": {"ok": False, "error": str(e)}}
                )

        # prepare observation message (compact)
        obs_text = json.dumps({"observations": observations}, ensure_ascii=False)
        obs_text = truncate_text(obs_text, "observations")
        next_guidance = f"\nGuidance: {NEXT_HINT}" if NEXT_HINT else ""
        messages.append({"role": "user", "content": f"{obs_text}{next_guidance}"})
        NEXT_HINT = None  # one-shot

        if final_msg:
            ok(f"Final: {final_msg}")
            break

    RUNNING = False
    ok("Coder session finished.")


# --------------- CLI commands ---------------
def help_text():
    print(hr())
    info("LMArena Coder CLI")
    print("  /help                    Show help")
    print("  /status                  Show state")
    print("  /capture                 Capture IDs (then click Retry in LMArena)")
    print("  /setids <sess> <msg>     Set IDs manually")
    print("  /root <dir>              Set path jail root (default: cwd)")
    print("  /confirm on|off          Toggle confirm for run_cmd (default: on)")
    print("  /cancel                  Cancel current streaming step")
    print("  /backend polling|openai [base_url]  Set coder backend")
    print("  /api.key <key>           Set Authorization for openai backend")
    print('  /code "<goal>" [--steps=20] [--window=12] [--timeout=180] [--hint="..."]')
    print("  /pause | /resume | /stop Pause/resume/stop coder session")
    print("  /mono                    Toggle monochrome")
    print("  /exit                    Quit")
    print(hr())


def show_status():
    info("Status:")
    print(f"  Browser polling: {'yes' if CLIENT_SEEN else 'no'}")
    print(f"  IDs: session={SESSION_ID or '-'} message={MESSAGE_ID or '-'}")
    print(f"  Root: {ROOT}")
    print(f"  Confirm run: {CONFIRM_RUN}")
    print(f"  History window: {HISTORY_WINDOW}")
    print(f"  Running: {RUNNING}  Paused: {PAUSED}  Timeout: {STEP_TIMEOUT}s")


def prompt():
    print(f"{C.INFO}> {C.R}", end="", flush=True)


async def repl():
    global CAPTURE_FLAG, SESSION_ID, MESSAGE_ID, ROOT, CONFIRM_RUN, STEP_TIMEOUT, HISTORY_WINDOW
    global RUNNING, PAUSED, NEXT_HINT

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

            if cmd == "/help":
                help_text()
            elif cmd == "/exit":
                print("Bye.")
                raise SystemExit(0)
            elif cmd == "/status":
                show_status()
            elif cmd == "/capture":
                CAPTURE_FLAG = True
                ok("Capture ON → click Retry in LMArena.")
            elif cmd == "/setids" and len(parts) >= 3:
                SESSION_ID, MESSAGE_ID = parts[1], parts[2]
                ok("IDs set.")
            elif cmd == "/root" and len(parts) >= 2:
                newr = Path(parts[1]).expanduser().resolve()
                if not newr.exists():
                    err("Root not found.")
                else:
                    ROOT = newr
                    ok(f"Root set → {ROOT}")
            elif cmd == "/confirm" and len(parts) >= 2:
                val = parts[1].strip().lower()
                if val in ("on", "off"):
                    CONFIRM_RUN = val == "on"
                    ok(f"Confirm run: {CONFIRM_RUN}")
                else:
                    err("Use /confirm on|off")
            elif cmd == "/cancel":
                from builtins import globals as _g

                _g()["CANCEL_REQUESTED"] = True
                ok("Cancel requested (will stop current stream).")
            elif cmd == "/backend":
                toks = line.split()
                if len(toks) >= 2 and toks[1] in ("polling", "openai"):
                    BACKEND = toks[1]
                    if len(toks) >= 3:
                        OPENAI_BASE = toks[2]
                    ok(
                        f"Backend={BACKEND} base={OPENAI_BASE if BACKEND=='openai' else '(polling)'}"
                    )
                else:
                    err("Usage: /backend polling|openai [base_url]")
            elif cmd == "/api.key":
                if len(parts) >= 2:
                    OPENAI_API_KEY = parts[1].strip()
                    ok("API key set.")
                else:
                    err("Usage: /api.key <key>")
            elif cmd == "/mono":
                global USE_COLOR
                USE_COLOR = not USE_COLOR
                _apply_colors()
                ok(f"Monochrome {'ON' if not USE_COLOR else 'OFF'}")
            elif cmd == "/pause":
                if RUNNING:
                    global PAUSED
                    PAUSED = True
                    ok("Paused.")
                else:
                    warn("Not running.")
            elif cmd == "/resume":
                if RUNNING:
                    PAUSED = False
                    ok("Resumed.")
                else:
                    warn("Not running.")
            elif cmd == "/stop":
                if RUNNING:
                    RUNNING = False
                    PAUSED = False
                    ok("Stopping after current step…")
                else:
                    warn("Not running.")
            elif cmd == "/code":
                if len(parts) < 2:
                    err(
                        'Usage: /code "<goal>" [--steps=20] [--window=12] [--timeout=180] [--hint="..."]'
                    )
                    prompt()
                    continue
                # naive parse
                goal_match = re.findall(r'"([^"]+)"', line)
                if not goal_match:
                    err('Provide goal in quotes, e.g., /code "Add tests and fix bug X"')
                    prompt()
                    continue
                goal = goal_match[0]
                steps = STEP_MAX
                window = HISTORY_WINDOW
                hint = None
                timeout = STEP_TIMEOUT
                for tk in line.split():
                    if tk.startswith("--steps="):
                        try:
                            steps = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--window="):
                        try:
                            window = int(tk.split("=", 1)[1])
                        except:
                            pass
                    elif tk.startswith("--timeout="):
                        try:
                            timeout = float(tk.split("=", 1)[1])
                        except:
                            pass
                # separate hint (allow spaces)
                m = re.search(r"--hint=(.+)$", line)
                if m:
                    hint = m.group(1).strip()
                    if hint.startswith('"') and hint.endswith('"') and len(hint) >= 2:
                        hint = hint[1:-1]
                HISTORY_WINDOW = window
                STEP_TIMEOUT = timeout
                if RUNNING:
                    warn("Already running. Use /stop first.")
                else:
                    asyncio.create_task(coder_session(goal, steps, window, hint))
                    ok("Coder session started.")

            else:
                warn("Unknown command. /help for help.")
            prompt()
            continue

        # free text -> do nothing (we don't chat in coder CLI)
        warn("Use /code to start a coding session, or /help for commands.")
        prompt()


# --------------- App bootstrap ---------------
def main():
    app = web.Application()
    app.router.add_get("/bridge/poll", bridge_poll)
    app.router.add_post("/bridge/push", bridge_push)
    app.router.add_route(
        "OPTIONS", "/bridge/push", lambda r: _add_cors(web.Response(text=""))
    )
    app.router.add_post("/internal/id_capture/update", id_capture_update)
    app.router.add_route(
        "OPTIONS",
        "/internal/id_capture/update",
        lambda r: _add_cors(web.Response(text="")),
    )
    app.router.add_get("/internal/healthz", healthz)

    runner = web.AppRunner(app)

    async def _run():
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 5102)
        await site.start()
        info("Listening on:")
        print("  GET  http://127.0.0.1:5102/bridge/poll")
        print("  POST http://127.0.0.1:5102/bridge/push")
        print("  POST http://127.0.0.1:5102/internal/id_capture/update")
        help_text()
        await repl()

    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(runner.cleanup())
            loop.close()
        except Exception:
            pass


async def repl_ptk():
    global CANCEL_REQUESTED, RUNNING, PAUSED
    session = PromptSession()
    kb = KeyBindings()

    @kb.add("c-c")
    def _(event):
        globals()["CANCEL_REQUESTED"] = True

    @kb.add("c-x")
    def _(event):
        raise SystemExit(0)

    help_text()
    prompt()
    while True:
        try:
            line = await session.prompt_async("> ", key_bindings=kb)
        except (EOFError, KeyboardInterrupt):
            CANCEL_REQUESTED = True
            continue
        if line is None:
            continue
        # reuse existing repl handler by injecting into stdin is messy; simplest: copy minimal switch here — or skip using PTK loop for now
        # For safety, stick with the classic repl(); PTK remains available for future refactor.
        # (Keep placeholder so we can finalize in next pass.)
        pass


if __name__ == "__main__":
    main()
