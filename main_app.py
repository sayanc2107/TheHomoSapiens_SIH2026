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

# 1. Auto-download the modern hand landmarker model from Google
MODEL_PATH = 'hand_landmarker.task'
if not os.path.exists(MODEL_PATH):
    print("Downloading MediaPipe model from Google...")
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    urllib.request.urlretrieve(url, MODEL_PATH)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Initialize the modern Tasks API
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

# 3. ASL Gesture Recognition Logic
def recognize_gesture(hand_landmarks):
    # Helper function to check if a finger is extended (open)
    def is_open(tip, middle_joint):
        return hand_landmarks[tip].y < hand_landmarks[middle_joint].y

    # Check the state of the four fingers
    index_open = is_open(8, 6)
    middle_open = is_open(12, 10)
    ring_open = is_open(16, 14)
    pinky_open = is_open(20, 18)

    # Thumb logic: checking if thumb tip is further out (x-axis) than the thumb base
    thumb_open = hand_landmarks[4].x < hand_landmarks[3].x if hand_landmarks[0].x > hand_landmarks[9].x else hand_landmarks[4].x > hand_landmarks[3].x

    # --- ASL Letter Dictionary Logic ---
    if index_open and middle_open and ring_open and pinky_open and not thumb_open:
        return "B"
    elif index_open and middle_open and ring_open and not pinky_open and not thumb_open:
        return "W"
    elif index_open and middle_open and not ring_open and not pinky_open and not thumb_open:
        return "V"
    elif thumb_open and index_open and not middle_open and not ring_open and not pinky_open:
        return "L"
    elif thumb_open and not index_open and not middle_open and not ring_open and pinky_open:
        return "Y"
    elif not thumb_open and not index_open and not middle_open and not ring_open and pinky_open:
        return "I"
    elif not thumb_open and index_open and not middle_open and not ring_open and not pinky_open:
        return "D"
    elif thumb_open and not index_open and not middle_open and not ring_open and not pinky_open:
        return "A"
        
    return "Sign not recognized..."

# 4. WebSocket Endpoint for live video frames
@app.websocket("/ws/translate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive the frame from the frontend
            data = await websocket.receive_text()
            img_data = base64.b64decode(data.split(',')[1])
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            # Format for the Tasks API
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
            
            # Process the frame
            detection_result = detector.detect(mp_image)
            
            translation = "No hand detected"
            
            if detection_result.hand_landmarks:
                for hand_landmarks in detection_result.hand_landmarks:
                    translation = recognize_gesture(hand_landmarks)
                    break 
                    
            await websocket.send_json({"translation": translation})
            
    except WebSocketDisconnect:
        print("Client disconnected")