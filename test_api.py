import httpx
from datetime import datetime
import base64

def test():
    # Construct a minimal valid ImageFrame payload
    payload = {
        "frame_id": "test_frame_1",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "image_data": base64.b64encode(b"test image").decode("ascii"),
        "width": 640,
        "height": 480,
        "exposure_ms": 10.0,
        "metadata": {}
    }
    
    try:
        print("Sending POST request to /frames...")
        response = httpx.post("http://127.0.0.1:8000/frames", json=payload, timeout=10.0)
        print("Status code:", response.status_code)
        print("Response text:", response.text)
    except Exception as e:
        print("Error occurred:")
        print(type(e).__name__, e)

if __name__ == "__main__":
    test()
