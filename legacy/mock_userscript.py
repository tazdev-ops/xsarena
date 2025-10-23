"""
Mock userscript for development and testing purposes.

This script simulates the real userscript by connecting to the bridge server via WebSocket,
receiving payloads, and sending back mock responses via WebSocket instead of HTTP POSTs.
It serves as a development helper to test the bridge without requiring a real browser.
"""

import asyncio
import json

import websockets


async def mock_userscript():
    uri = "ws://127.0.0.1:5102/ws"
    async with websockets.connect(uri) as websocket:
        print("Connected to bridge server.")
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)

                # Handle commands from bridge
                if data.get("command"):
                    command = data["command"]
                    print(f"Received command: {command}")
                    # For now, we just acknowledge commands without specific action
                    continue

                # Handle payload requests from bridge
                if data.get("payload"):
                    request_id = data["request_id"]
                    payload = data["payload"]
                    print(f"Received job for request_id {request_id}:", payload)

                    # Send back mock chunks via WebSocket
                    mock_chunks = [
                        "This is a mocked response chunk 1.",
                        "This is a mocked response chunk 2.",
                        "This is a mocked response chunk 3.",
                    ]

                    for chunk in mock_chunks:
                        response_data = {"request_id": request_id, "data": chunk}
                        await websocket.send(json.dumps(response_data))
                        print(f"Sent chunk: {chunk}")
                        # Small delay between chunks to simulate streaming
                        await asyncio.sleep(0.1)

                    # Send the final [DONE] message
                    done_data = {"request_id": request_id, "data": "[DONE]"}
                    await websocket.send(json.dumps(done_data))
                    print("Sent [DONE] message")

            except websockets.exceptions.ConnectionClosed:
                print("Connection to bridge server closed.")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                break


if __name__ == "__main__":
    asyncio.run(mock_userscript())
