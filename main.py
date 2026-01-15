import os
import requests
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory store for tracking the last image per uid
user_history = {}

# API Keys list
nano_keys = [
    "4603e4f0febe2137d2b61a2445876c81",
    "44529f05230cc84b901fbf642b6747e1",
    "1150119bebb0ff7a8874366468a27508",
    "f434f443c9f6de5edcfc41269095fb74",
    "ba92878f6d170ab97462f6c7a7ab8245",
    "6f9c3c2b42ff4740971d77e21e004208",
    "c3ba79743a9093729a685c0f78b524ff"
]
nano_key_index = 0

KIE_API_KEY = os.environ.get("KIE_API_KEY")

NANO_BASE_URL = "https://api.nanobananaapi.ai/api/v1/nanobanana"
KIE_BASE_URL = "https://api.kie.ai/api/v1/jobs"

def get_next_nano_key():
    global nano_key_index
    if not nano_keys:
        return None
    key = nano_keys[nano_key_index]
    nano_key_index = (nano_key_index + 1) % len(nano_keys)
    return key

def poll_nano_task(task_id, api_key):
    """Poll for Nano Banana task completion"""
    max_attempts = 60
    for _ in range(max_attempts):
        try:
            response = requests.get(
                f"{NANO_BASE_URL}/record-info",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"taskId": task_id},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                
                # Check for failure in the response itself
                if data.get("code") != 200 and data.get("code") != 0:
                    return {"error": data.get("msg", "API Error"), "code": data.get("code")}

                res_data = data.get("data")
                if isinstance(res_data, dict):
                    # Check for resultImageUrl in response object
                    info = res_data.get("response") or res_data.get("info")
                    if isinstance(info, dict) and info.get("resultImageUrl"):
                        return {"resultats_url": info.get("resultImageUrl")}
                    
                    # Check directly in data
                    if res_data.get("resultImageUrl"):
                        return {"resultats_url": res_data.get("resultImageUrl")}
                
                # Top level check
                if data.get("resultImageUrl"):
                    return {"resultats_url": data.get("resultImageUrl")}
                    
            time.sleep(1.0) # Reduced from 1.5s for faster response
        except Exception:
            pass
    return None

def poll_kie_task(task_id):
    """Poll for Kie.ai task completion"""
    max_attempts = 60
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
                if not data:
                    time.sleep(2)
                    continue
                
                # Check for error in response
                if data.get("code") is not None and data.get("code") not in [0, 200] and data.get("msg"):
                    print(f"Kie API Error: {data.get('msg')}")
                    return data

                # Check multiple potential result locations
                res_data = data.get("data")
                if isinstance(res_data, dict):
                    # In some versions it's data.response.resultImageUrl
                    res = res_data.get("response") or res_data.get("info")
                    if isinstance(res, dict) and res.get("resultImageUrl"):
                        return {"resultats_url": res.get("resultImageUrl")}
                    
                    # Check for result images in standard Kie arrays
                    if res_data.get("images") and isinstance(res_data["images"], list) and len(res_data["images"]) > 0:
                        return {"resultats_url": res_data["images"][0]}
                    
                    # In others it's data.resultImageUrl
                    if res_data.get("resultImageUrl"):
                        return {"resultats_url": res_data.get("resultImageUrl")}
                
                # Check top level
                if data.get("resultImageUrl"):
                    return {"resultats_url": data.get("resultImageUrl")}
            time.sleep(2)
        except Exception as e:
            print(f"Kie Polling error: {e}")
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

    # Try keys in rotation
    attempts = 0
    max_keys = len(nano_keys)
    
    while attempts < max_keys:
        current_key = get_next_nano_key()
        if not current_key:
            return jsonify({"error": "No API keys available"}), 500
            
        try:
            submit_response = requests.post(
                f"{NANO_BASE_URL}/generate",
                json=payload,
                headers={
                    "Authorization": f"Bearer {current_key}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            
            if submit_response.status_code == 200:
                submit_data = submit_response.json()
                if not submit_data:
                    attempts += 1
                    continue
                task_id = submit_data.get("data", {}).get("taskId") if isinstance(submit_data.get("data"), dict) else submit_data.get("taskId")
                if task_id:
                    result = poll_nano_task(task_id, current_key)
                    return jsonify(result) if result else jsonify({"error": "Timeout", "taskId": task_id}), 504
            
            # Check for quota or credit error (402, 403, 429) to rotate
            if submit_response.status_code in [402, 403, 429]:
                attempts += 1
                continue
            
            # Additional check for 200 responses that contain error codes like 402 in JSON
            try:
                error_data = submit_response.json()
                if isinstance(error_data, dict) and error_data.get("code") == 402:
                    attempts += 1
                    continue
            except:
                pass

            return jsonify({"error": "Submit failed", "details": submit_response.text}), submit_response.status_code
                
        except Exception as e:
            attempts += 1
            if attempts >= max_keys:
                return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "All API keys exhausted or failed"}), 429

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
            "image_urls": [image_url],
            "aspect_ratio": "1:1",
            "quality": "basic"
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
            if not submit_data:
                return jsonify({"error": "Empty response from API"}), 500
            
            # Special check for Kie API status within 200 response
            if submit_data.get("code") != 200 and submit_data.get("code") != 0:
                return jsonify({"error": "Kie API error", "details": submit_data}), 400

            task_id = None
            if isinstance(submit_data.get("data"), dict):
                task_id = submit_data.get("data").get("taskId") or submit_data.get("data").get("recordId")
            else:
                task_id = submit_data.get("taskId")

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
