import asyncio
import websockets

async def test_ws():
    uri = "ws://127.0.0.1:8000/ws/live"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for messages...")
            for _ in range(3):
                message = await websocket.recv()
                print(f"Received message of length: {len(message)}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
