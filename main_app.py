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

def recognize_gesture(hand_landmarks):
    # 4 is the Thumb tip, 8 is the Index finger tip
    thumb_tip = hand_landmarks[4]
    index_finger_tip = hand_landmarks[8]
    
    # Simple placeholder logic: is index finger higher than thumb?
    if index_finger_tip.y < thumb_tip.y:
        return "Index finger up (Placeholder)"
    return "Waiting for sign..."

@app.websocket("/ws/translate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 3. Receive the frame from the frontend
            data = await websocket.receive_text()
            img_data = base64.b64decode(data.split(',')[1])
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            # 4. Format for the Tasks API
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
            
            # 5. Process the frame
            detection_result = detector.detect(mp_image)
            
            translation = "No hand detected"
            
            if detection_result.hand_landmarks:
                for hand_landmarks in detection_result.hand_landmarks:
                    translation = recognize_gesture(hand_landmarks)
                    break 
                    
            await websocket.send_json({"translation": translation})
            
    except WebSocketDisconnect:
        print("Client disconnected")