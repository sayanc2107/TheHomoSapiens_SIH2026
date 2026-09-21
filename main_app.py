import os
import cv2
import numpy as np
import base64
import urllib.request
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. Download the pre-trained model if it doesn't exist
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
MODEL_PATH = "gesture_recognizer.task"

if not os.path.exists(MODEL_PATH):
    print("Downloading pre-trained gesture model from Google...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Download complete.")

# 2. Initialize the Gesture Recognizer API with STRICTER thresholds (85%)
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)

options = vision.GestureRecognizerOptions(
    base_options=base_options, 
    num_hands=1,
    min_hand_detection_confidence=0.85,   # Must be 85% sure it's a hand (fixes pink pillow issue)
    min_hand_presence_confidence=0.85,    # Must be 85% sure the hand is still there
    min_tracking_confidence=0.85          # Stricter skeleton tracking
)
recognizer = vision.GestureRecognizer.create_from_options(options)

# 3. Expanded Gesture Dictionary
# Note: MediaPipe's default model recognizes 7 basic shapes. 
# We are adding your requested custom signs here so the backend is ready 
# for when you load your custom .h5/.onnx model later!
gesture_map = {
    "Thumb_Up": "👍 Good / Yes",
    "Thumb_Down": "👎 Bad / No",
    "Victory": "✌️ Victory / Two",
    "Open_Palm": "✋ Wait / Stop",
    "Closed_Fist": "✊ Solid / Fist",
    "ILoveYou": "🤟 I Love You",
    "Pointing_Up": "☝️ Up / One",
    "PointingAtUser": "🫵🏻 Pointing at You",
    "Call_Me": "🤙 Call Me",
    "Rock_On": "🤘 Rock On",
    "Fist_Bump": "👊🏻 Fist Bump",
    "High_Five": "🖐 High Five",
    "PinchedHand": "🤌🏻 Pinched Hand",
    "Pinching": "🤏 Pinching",
    "PinchedFingers": "🫰🏻 Pinched Fingers",
    "None": "Sign not recognized..."
}

# 4. FastAPI Setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep-Alive Route for UptimeRobot (Prevents cold starts)
@app.get("/")
def read_root():
    return {"status": "Active", "message": "TheHomoSapiens SIH 2026 Backend is running."}

# 5. WebSocket Endpoint for Real-Time Video Processing
@app.websocket("/ws/translate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive base64 frame from frontend
            data = await websocket.receive_text()
            
            # Decode the base64 image
            header, encoded = data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None:
                continue

            # Convert to MediaPipe Image format
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            
            # Process the image
            recognition_result = recognizer.recognize(mp_image)
            
            response = {
                "translation": "No hand detected",
                "landmarks": []
            }
            
            # If a hand is found, extract landmarks and gesture
            if recognition_result.hand_landmarks:
                # Extract coordinates for frontend canvas drawing
                landmarks = recognition_result.hand_landmarks[0]
                response["landmarks"] = [{"x": lm.x, "y": lm.y, "z": lm.z} for lm in landmarks]
                
                # Extract gesture classification
                if recognition_result.gestures and len(recognition_result.gestures[0]) > 0:
                    top_gesture = recognition_result.gestures[0][0].category_name
                    
                    # Map to our dictionary, default to "None" if not found
                    if top_gesture == "" or top_gesture == "None":
                        response["translation"] = "Sign not recognized..."
                    else:
                        response["translation"] = gesture_map.get(top_gesture, "Sign not recognized...")
                else:
                    response["translation"] = "Sign not recognized..."
            
            # Send the JSON payload back to the frontend
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"WebSocket Error: {e}")