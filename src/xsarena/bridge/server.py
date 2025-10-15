"""CSP-safe bridge server for XSArena."""

import argparse
import asyncio
import logging
import os
from typing import Dict

from aiohttp import web

routes = web.RouteTableDef()

# Global storage for messages and responses (in a real implementation, use a more robust solution)
message_queues: Dict[str, asyncio.Queue] = {}
response_callbacks: Dict[str, asyncio.Queue] = {}


@routes.post("/v1/chat/completions")
async def handle_chat_completions(request):
    """Handle chat completion requests from the backend."""
    data = await request.json()

    # Extract messages from the request
    messages = data.get("messages", [])
    stream = data.get("stream", False)

    # Generate a session ID for this conversation
    import uuid

    session_id = str(uuid.uuid4())

    # Store the messages in a queue for the LLM to process
    if session_id not in message_queues:
        message_queues[session_id] = asyncio.Queue()

    # Add the messages to the queue
    await message_queues[session_id].put(messages)

    # Wait for the response (in a real implementation, this would be handled by the LLM client)
    if session_id not in response_callbacks:
        response_callbacks[session_id] = asyncio.Queue()

    try:
        # Wait for a response with a timeout
        response = await asyncio.wait_for(
            response_callbacks[session_id].get(), timeout=300
        )  # 5 minute timeout

        return web.json_response(
            {
                "id": f"chatcmpl-{session_id}",
                "object": "chat.completion",
                "created": int(asyncio.get_event_loop().time()),
                "model": data.get("model", "default"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": response},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": len(str(messages)),
                    "completion_tokens": len(response),
                    "total_tokens": len(str(messages)) + len(response),
                },
            }
        )
    except asyncio.TimeoutError:
        return web.json_response(
            {"error": {"type": "timeout", "message": "Request timed out"}}, status=408
        )


@routes.post("/push_response")
async def push_response(request):
    """Endpoint for pushing responses back to the server."""
    data = await request.json()
    session_id = data.get("session_id")
    response = data.get("response", "")

    if session_id and session_id in response_callbacks:
        await response_callbacks[session_id].put(response)
        return web.json_response({"status": "success"})
    else:
        return web.json_response(
            {"status": "error", "message": "Invalid session ID"}, status=400
        )


@routes.get("/health")
async def health_check(request):
    """Health check endpoint."""
    return web.json_response({"status": "healthy"})


def main():
    """Run the bridge server with configurable port."""
    parser = argparse.ArgumentParser(description="XSArena Bridge Server")
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=int(os.getenv("XSA_PORT", os.getenv("LMA_PORT", "8080"))),
        help="Local bridge port (default from XSA_PORT, LMA_PORT, or 8080)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("XSA_HOST", os.getenv("LMA_HOST", "127.0.0.1")),
        help="Local bridge host (default from XSA_HOST, LMA_HOST, or 127.0.0.1)",
    )
    args = parser.parse_args()

    @web.middleware
    async def cors_middleware(request, handler):
        if request.method == "OPTIONS":
            resp = web.Response()
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return resp
        resp = await handler(request)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return resp

    app = web.Application(middlewares=[cors_middleware])

    @routes.options("/v1/chat/completions")
    @routes.options("/push_response")
    @routes.options("/health")
    async def options_handler(_request):
        return web.Response()  # cors_middleware will set headers

    # register routes after all route functions (including OPTIONS) are defined
    app.add_routes(routes)

    logging.basicConfig(level=logging.INFO)

    # Set up the app runner
    runner = web.AppRunner(app)

    async def _run():
        await runner.setup()
        site = web.TCPSite(runner, args.host, args.port)
        await site.start()
        logging.info("Bridge server listening on:")
        print(f"  GET  http://{args.host}:{args.port}/health")
        print(f"  POST http://{args.host}:{args.port}/v1/chat/completions")
        print(f"  POST http://{args.host}:{args.port}/push_response")
        print(f"  Bridge server ready on http://{args.host}:{args.port}")

    try:
        asyncio.run(_run())
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down bridge server...")
    finally:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(runner.cleanup())
            loop.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
