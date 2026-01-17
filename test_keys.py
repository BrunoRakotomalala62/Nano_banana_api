import requests
import os

nano_keys = [
    "4603e4f0febe2137d2b61a2445876c81",
    "44529f05230cc84b901fbf642b6747e1",
    "1150119bebb0ff7a8874366468a27508",
    "f434f443c9f6de5edcfc41269095fb74",
    "ba92878f6d170ab97462f6c7a7ab8245",
    "6f9c3c2b42ff4740971d77e21e004208",
    "c3ba79743a9093729a685c0f78b524ff",
    "f05e95578ebf98eae1513481a360bb5b",
    "e654dd8c8e8e90b8c1cb337dbc4d7ad6",
    "3f5cba5262dd27984dbf17cb2f80fd90",
    "ff19d714b0997907be9de3f2007f944e",
    "87b94e9ca520e45fba5668a645fb5d42",
    "97557efa267f1ecabca345d4d8b1d272",
    "457f0061c9449372ec151886ce5ba395",
    "f1226514bcfe5900a8addd5af1291ce2",
    "5a9605aa8a453d666ca3a42a43f68f9e",
    "dc5ea87ee94a54d7c4c12b7e910d16c6",
    "d1a755e52975441f6faf0c6b7d5fc4dc",
    "1885327d1ac85c814eddf90f10e28245",
    "2ae2fa97faf4fdc71de2fd5a51d7eeb1"
]

NANO_BASE_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana"

working_keys = []

print(f"Testing {len(nano_keys)} keys...")

for key in nano_keys:
    try:
        # We'll use a dummy prompt to test the key
        payload = {
            "prompt": "test",
            "type": "IMAGETOIAMGE",
            "imageUrls": ["https://example.com/image.jpg"],
            "numImages": 1,
            "imageSize": "1:1",
            "watermark": ""
        }
        response = requests.post(
            f"{NANO_BASE_URL}/generate",
            json=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        data = response.json()
        # If it returns a task ID or doesn't return quota/auth errors, it's likely working or at least valid
        if response.status_code == 200:
            if data.get("code") not in [402, 403, 429]:
                print(f"Key {key} seems WORKING (Code: {data.get('code')})")
                working_keys.append(key)
            else:
                print(f"Key {key} FAILED (Code: {data.get('code')}, Msg: {data.get('msg')})")
        else:
            print(f"Key {key} FAILED (HTTP {response.status_code})")
    except Exception as e:
        print(f"Key {key} ERRORED: {e}")

with open("api.txt", "w") as f:
    for wk in working_keys:
        f.write(wk + "\n")

print(f"\nFound {len(working_keys)} working keys. Saved to api.txt")
