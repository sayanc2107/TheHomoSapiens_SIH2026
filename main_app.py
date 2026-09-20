import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from collections import deque
# import tensorflow as tf # Uncomment when your model is ready

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# 1. Initialize MediaPipe (Upgraded to 2 hands for ISL)
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2)
detector = vision.HandLandmarker.create_from_options(options)

# 2. Load your custom trained ISL model (Placeholder)
# isl_model = tf.keras.models.load_model('sih_isl_model.h5')

# 3. List of your 63 words from sigh-lang.JPG
actions = np.array(['Hello', 'Namaste', 'Thank You', 'Water', 'College', 'Hospital']) # Add all 63 here

# 4. Sequence tracking (Holds the last 30 frames of data)
sequence = deque(maxlen=30)

def extract_keypoints(detection_result):
    """Flattens 2 hands (21 joints * 3 coordinates = 126 values) into a single array"""
    hand1 = np.zeros(21 * 3)
    hand2 = np.zeros(21 * 3)
    
    if detection_result.hand_landmarks:
        # Extract Hand 1
        hand1 = np.array([[res.x, res.y, res.z] for res in detection_result.hand_landmarks[0]]).flatten()
        # Extract Hand 2 if visible
        if len(detection_result.hand_landmarks) > 1:
            hand2 = np.array([[res.x, res.y, res.z] for res in detection_result.hand_landmarks[1]]).flatten()
            
    return np.concatenate([hand1, hand2])

@app.websocket("/ws/translate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    translation = "Waiting for gesture..."
    
    try:
        while True:
            data = await websocket.receive_text()
            img_data = base64.b64decode(data.split(',')[1])
            np_arr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            detection_result = detector.detect(mp_image)
            
            # Extract points and add to our rolling 30-frame sequence
            keypoints = extract_keypoints(detection_result)
            sequence.append(keypoints)
            
            # Only predict if we have a full 30 frames of motion history
            if len(sequence) == 30:
                # PREDICTION LOGIC (Uncomment when model is trained)
                # res = isl_model.predict(np.expand_dims(sequence, axis=0))[0]
                # translation = actions[np.argmax(res)]
                translation = "Sequence buffer full - Ready for ML Model"
            
            # Send coordinates for canvas overlay
            landmarks_data = []
            if detection_result.hand_landmarks:
                # Send points for all visible hands
                for hand_lms in detection_result.hand_landmarks:
                    landmarks_data.extend([{"x": lm.x, "y": lm.y} for lm in hand_lms])
                    
            await websocket.send_json({"translation": translation, "landmarks": landmarks_data})
            
    except WebSocketDisconnect:
        print("Client disconnected")