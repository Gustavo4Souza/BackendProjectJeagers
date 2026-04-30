import asyncio
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

import websockets


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WS_BASE_URL = os.getenv("WS_BASE_URL", "ws://localhost:8000")
FERMENTER_ID = os.getenv("FERMENTER_ID", "fermenter-001")
CLIENT_COUNT = int(os.getenv("CLIENT_COUNT", "3"))


async def websocket_client(name: str, ready: asyncio.Queue, messages: list):
    url = f"{WS_BASE_URL}/ws/fermenters/{FERMENTER_ID}"

    async with websockets.connect(url) as websocket:
        await ready.put(name)
        message = await asyncio.wait_for(websocket.recv(), timeout=10)
        messages.append((name, json.loads(message)))


def publish_reading():
    payload = {
        "fermenter_id": FERMENTER_ID,
        "metric": "temperature",
        "value": 25.4,
        "unit": "celsius",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE_URL}/api/v1/readings",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        raise RuntimeError(f"POST failed with {error.code}: {body}") from error


async def main():
    ready = asyncio.Queue()
    messages = []
    clients = [
        asyncio.create_task(websocket_client(f"client-{index + 1}", ready, messages))
        for index in range(CLIENT_COUNT)
    ]

    for _ in clients:
        await asyncio.wait_for(ready.get(), timeout=10)

    status, created_reading = await asyncio.to_thread(publish_reading)
    await asyncio.gather(*clients)

    print(f"POST /api/v1/readings -> {status}")
    print(json.dumps(created_reading, indent=2))
    print(f"WebSocket messages received: {len(messages)}/{CLIENT_COUNT}")

    for client_name, message in messages:
        print(f"{client_name}: {json.dumps(message, sort_keys=True)}")

    if len(messages) != CLIENT_COUNT:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
