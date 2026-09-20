import cv2
import mediapipe as mp
import numpy as np
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

def recognize_gesture(hand_landmarks):
    # Placeholder for your actual ASL logic or Keras/TensorFlow model
    # For now, it uses a basic heuristic: checking if the index finger is raised
    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    index_finger_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    
    if index_finger_tip.y < thumb_tip.y:
        return "Index finger up (Placeholder)"
    return "Waiting for sign..."

@app.websocket("/ws/translate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 1. Receive base64 encoded image frame from frontend
            data = await websocket.receive_text()
            
            # 2. Decode base64 to OpenCV image format
            img_data = base64.b64decode(data.split(',')[1])
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            # 3. Process with MediaPipe
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            result = hands.process(img_rgb)
            
            translation = "No hand detected"
            
            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    translation = recognize_gesture(hand_landmarks)
                    break # Processing one hand for speed
                    
            # 4. Send translation back to the frontend
            await websocket.send_json({"translation": translation})
            
    except WebSocketDisconnect:
        print("Client disconnected")