#!/usr/bin/env python3
"""
Bridge I/O functions extracted from interactive.py
"""

from aiohttp import web


def _add_cors(resp: web.StreamResponse):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Private-Network"] = "true"
    return resp


async def bridge_poll(request, state):
    """
    Args:
        request: web.Request
        state: dict containing shared state like CAPTURE_FLAG, PENDING_JOBS, CLIENT_SEEN, etc.
    """
    first = not state["CLIENT_SEEN"]
    state["CLIENT_SEEN"] = True
    resp = {"hello": True, "capture": state["CAPTURE_FLAG"], "job": None}
    if state["CAPTURE_FLAG"]:
        state["CAPTURE_FLAG"] = False
    if state["PENDING_JOBS"]:
        resp["job"] = state["PENDING_JOBS"].pop(0)
    if first:
        print()
        state["ok"](f"[{state['now']()}] Browser polling active.")
        print("> ", end="", flush=True)
    return _add_cors(web.json_response(resp))


async def bridge_push(request, state):
    """
    Args:
        request: web.Request
        state: dict containing shared state like RESPONSE_CHANNELS
    """
    try:
        data = await request.json()
        req_id = data.get("request_id")
        payload = data.get("data")
        if not req_id:
            return _add_cors(
                web.json_response({"error": "missing request_id"}, status=400)
            )
        q = state["RESPONSE_CHANNELS"].get(req_id)
        if q:
            await q.put(payload)
        return _add_cors(web.json_response({"status": "ok"}))
    except Exception as e:
        return _add_cors(web.json_response({"error": str(e)}, status=500))


async def id_capture_update(request, state):
    """
    Args:
        request: web.Request
        state: dict containing shared state like SESSION_ID, MESSAGE_ID, etc.
    """
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
        state["SESSION_ID"], state["MESSAGE_ID"] = sid, mid
        print()
        state["ok"](f"[{state['now']()}] IDs updated:")
        print(
            f"    session_id = {state['SESSION_ID']}\n    message_id = {state['MESSAGE_ID']}"
        )
        print("> ", end="", flush=True)
        return _add_cors(web.json_response({"status": "ok"}))
    except Exception as e:
        return _add_cors(web.json_response({"error": str(e)}, status=500))


async def healthz(_req, state):
    """
    Args:
        _req: web.Request (unused)
        state: dict containing shared state (unused here)
    """
    return web.json_response({"status": "ok"})
