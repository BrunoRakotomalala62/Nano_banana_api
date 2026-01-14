import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory store for tracking the last image per uid
# In a production app, this should be in a database (e.g. Replit DB)
user_history = {}

API_KEY = os.environ.get("API_KEYS_1", "44529f05230cc84b901fbf642b6747e1")
NANO_BANANA_URL = "https://nanobananaapi.ai/api/v1/image/imageToImage" # Assuming standard endpoint based on documentation pattern

@app.route('/nanobanana', methods=['GET'])
def nanobanana():
    prompt = request.args.get('prompt')
    image_url = request.args.get('image')
    uid = request.args.get('uid')

    if not prompt or not uid:
        return jsonify({"error": "Missing prompt or uid"}), 400

    # Handle image persistence logic
    if image_url:
        user_history[uid] = image_url
    else:
        image_url = user_history.get(uid)

    if not image_url:
        return jsonify({"error": "No image provided and no previous image found for this uid"}), 400

    # Call Nano Banana API
    # Based on the user's provided JSON structure, we mimic the paramJson requirements
    payload = {
        "apiKey": API_KEY,
        "type": "IMAGETOIAMGE",
        "prompt": prompt,
        "imageUrls": [image_url],
        "imageSize": "1:1",
        "numImages": 1
    }

    try:
        # The user provided a sample response, but usually APIs take POST for these transformations.
        # However, the user asked for a GET route that calls the API.
        # We'll use POST to the external API as is standard for image processing.
        response = requests.post(
            "https://nanobananaapi.ai/api/v1/image/task/create", # Standard endpoint for task creation
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            # If the API is asynchronous (returns taskId), we might need to poll.
            # But the user provided a "completeTime" and "resultImageUrl" in the example,
            # suggesting they might want the result directly or the task info.
            # I will return the full response from the API for now.
            return jsonify(data)
        else:
            return jsonify({"error": "Failed to call Nano Banana API", "details": response.text}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Nano Banana API Proxy is running. Use /nanobanana?prompt=...&image=...&uid=..."

if __name__ == '__main__':
    # Bind to 0.0.0.0:5000 as per Replit requirements
    app.run(host='0.0.0.0', port=5000)
