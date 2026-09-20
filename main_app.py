import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import base64
import urllib.request
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# 1. Auto-download the pre-trained Google Gesture Recognizer model
MODEL_PATH = 'gesture_recognizer.task'
if not os.path.exists(MODEL_PATH):
    print("Downloading pre-trained gesture model from Google...")
    url = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
    urllib.request.urlretrieve(url, MODEL_PATH)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Initialize the Gesture Recognizer API (It handles both landmarks AND gestures)
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.GestureRecognizerOptions(base_options=base_options, num_hands=1)
recognizer = vision.GestureRecognizer.create_from_options(options)

# 3. Helper to format Google's raw category names into SIH presentation strings
def format_gesture(category_name):
    gesture_map = {
        "Closed_Fist": "✊ Closed Fist",
        "Open_Palm": "✋ Wait / Stop",
        "Pointing_Up": "☝️ Pointing Up",
        "Thumb_Down": "👎 Bad / No",
        "Thumb_Up": "👍 Good / Yes",
        "Victory": "✌️ Victory / Peace",
        "ILoveYou": "🤟 I Love You",
        "None": "Sign not recognized..."
    }
    return gesture_map.get(category_name, category_name)

# 4. WebSocket Endpoint for live video frames
@app.websocket("/ws/translate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive and decode the frame
            data = await websocket.receive_text()
            img_data = base64.b64decode(data.split(',')[1])
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            # Format for the Tasks API
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
            
            # Process the frame for gestures and landmarks
            recognition_result = recognizer.recognize(mp_image)
            
            translation = "No hand detected"
            landmarks_data = []
            
            # If a hand is on screen and the model analyzed it
            if recognition_result.gestures and recognition_result.hand_landmarks:
                # 1. Get the translation
                top_gesture = recognition_result.gestures[0][0].category_name
                translation = format_gesture(top_gesture)
                
                # 2. Get the X/Y coordinates for the frontend skeleton overlay
                landmarks_data = [{"x": lm.x, "y": lm.y} for lm in recognition_result.hand_landmarks[0]]
                    
            await websocket.send_json({
                "translation": translation, 
                "landmarks": landmarks_data
            })
            
    except WebSocketDisconnect:
        print("Client disconnected")

# Keep-Alive route for UptimeRobot
@app.get("/")
def keep_alive():
    return {"status": "The Homo Sapiens backend is awake 24/7!"}