import os
import requests
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory store for tracking the last image per uid
user_history = {}

# API Keys from environment
NANO_API_KEY = os.environ.get("API_KEYS_1")
KIE_API_KEY = os.environ.get("KIE_API_KEY")

NANO_BASE_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana"
KIE_BASE_URL = "https://api.kie.ai/api/v1/jobs"

def poll_nano_task(task_id):
    """Poll for Nano Banana task completion"""
    max_attempts = 45
    for _ in range(max_attempts):
        try:
            response = requests.get(
                f"{NANO_BASE_URL}/record-info",
                headers={"Authorization": f"Bearer {NANO_API_KEY}"},
                params={"taskId": task_id},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                info = data.get("data", {}).get("info") or data.get("response") or data.get("info")
                if isinstance(info, dict) and info.get("resultImageUrl"):
                    return data
            time.sleep(2)
        except Exception:
            pass
    return None

def poll_kie_task(task_id):
    """Poll for Kie.ai task completion"""
    max_attempts = 60 # Increased polling time for Kie
    for _ in range(max_attempts):
        try:
            response = requests.get(
                f"{KIE_BASE_URL}/getTaskInfo",
                headers={"Authorization": f"Bearer {KIE_API_KEY}"},
                params={"taskId": task_id},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                
                # Check multiple potential result locations based on common Kie structures
                res_data = data.get("data", {})
                if isinstance(res_data, dict):
                    # Check in data.response or data.info
                    res = res_data.get("response") or res_data.get("info")
                    if isinstance(res, dict) and res.get("resultImageUrl"):
                        return data
                    
                    # Some versions might put result directly in data
                    if res_data.get("resultImageUrl"):
                        return data
                
                # Check top level
                if data.get("resultImageUrl"):
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

    if image_url:
        user_history[uid] = image_url
    else:
        image_url = user_history.get(uid)

    if not image_url:
        return jsonify({"error": "No image provided and no previous image found for this uid"}), 400

    payload = {
        "prompt": prompt,
        "type": "IMAGETOIAMGE",
        "imageUrls": [image_url],
        "numImages": 1,
        "imageSize": "1:1",
        "watermark": ""
    }

    try:
        submit_response = requests.post(
            f"{NANO_BASE_URL}/generate",
            json=payload,
            headers={
                "Authorization": f"Bearer {NANO_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if submit_response.status_code == 200:
            submit_data = submit_response.json()
            task_id = submit_data.get("data", {}).get("taskId") or submit_data.get("taskId")
            if task_id:
                result = poll_nano_task(task_id)
                return jsonify(result) if result else jsonify({"error": "Timeout", "taskId": task_id}), 504
        return jsonify({"error": "Submit failed", "details": submit_response.text}), submit_response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/kie', methods=['GET'])
def kie_api():
    prompt = request.args.get('prompt')
    image_url = request.args.get('image')
    uid = request.args.get('uid')

    if not prompt or not uid:
        return jsonify({"error": "Missing prompt or uid"}), 400

    if image_url:
        user_history[uid] = image_url
    else:
        image_url = user_history.get(uid)

    if not image_url:
        return jsonify({"error": "No image provided"}), 400

    payload = {
        "model": "seedream/4.5-edit",
        "input": {
            "prompt": prompt,
            "image_urls": [image_url]
        }
    }

    try:
        submit_response = requests.post(
            f"{KIE_BASE_URL}/createTask",
            json=payload,
            headers={
                "Authorization": f"Bearer {KIE_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if submit_response.status_code == 200:
            submit_data = submit_response.json()
            task_id = submit_data.get("data", {}).get("taskId")
            if task_id:
                result = poll_kie_task(task_id)
                return jsonify(result) if result else jsonify({"error": "Timeout", "taskId": task_id}), 504
        return jsonify({"error": "Submit failed", "details": submit_response.text}), submit_response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "API Proxy is running. Endpoints: /nanobanana, /kie"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
