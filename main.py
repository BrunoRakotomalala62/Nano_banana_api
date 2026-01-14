import os
import requests
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory store for tracking the last image per uid
user_history = {}

API_KEY = os.environ.get("API_KEYS_1", "44529f05230cc84b901fbf642b6747e1")
BASE_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana"

def get_task_result(task_id):
    """Poll for task completion"""
    max_attempts = 45  # Increased polling time
    for _ in range(max_attempts):
        try:
            response = requests.get(
                f"{BASE_URL}/record-info",
                headers={"Authorization": f"Bearer {API_KEY}"},
                params={"taskId": task_id},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                # Check for success in the response structure
                if isinstance(data, dict):
                    # Check the success flag or result image
                    success = data.get("successFlag") == 1 or data.get("code") == 200
                    
                    # Look for info in multiple possible locations
                    info = data.get("data", {}).get("info")
                    if not info:
                         info = data.get("response") or data.get("info")
                    
                    if isinstance(info, dict) and info.get("resultImageUrl"):
                        return data
            time.sleep(2)
        except Exception:
            pass
    return None

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
    payload = {
        "prompt": prompt,
        "type": "IMAGETOIAMGE",
        "imageUrls": [image_url],
        "numImages": 1,
        "imageSize": "1:1",
        "watermark": ""
    }

    try:
        # Submit task
        submit_response = requests.post(
            f"{BASE_URL}/generate",
            json=payload,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if submit_response.status_code == 200:
            try:
                submit_data = submit_response.json()
            except Exception as e:
                return jsonify({"error": "Failed to parse JSON response from Nano Banana API", "details": str(e), "raw": submit_response.text}), 500

            if isinstance(submit_data, dict):
                # Handle different possible response structures
                data_obj = submit_data.get("data")
                if isinstance(data_obj, dict):
                    task_id = data_obj.get("taskId")
                else:
                    task_id = submit_data.get("taskId")
                
                if not task_id:
                    return jsonify({
                        "error": "Failed to get taskId from Nano Banana API",
                        "details": submit_data
                    }), 500
                    
                # Wait for completion (polling)
                result = get_task_result(task_id)
                if result:
                    return jsonify(result)
                else:
                    return jsonify({
                        "error": "Timeout waiting for image generation",
                        "taskId": task_id
                    }), 504
            else:
                return jsonify({"error": "Unexpected response format from Nano Banana API", "details": str(submit_data)}), 500
        else:
            return jsonify({
                "error": "Failed to submit task to Nano Banana API",
                "status_code": submit_response.status_code,
                "details": submit_response.text[:500]
            }), submit_response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Nano Banana API Proxy is running. Use /nanobanana?prompt=...&image=...&uid=..."

if __name__ == '__main__':
    # Bind to 0.0.0.0:5000 as per Replit requirements
    app.run(host='0.0.0.0', port=5000)

@app.route('/')
def index():
    return "Nano Banana API Proxy is running. Use /nanobanana?prompt=...&image=...&uid=..."

if __name__ == '__main__':
    # Bind to 0.0.0.0:5000 as per Replit requirements
    app.run(host='0.0.0.0', port=5000)
