import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import os
import urllib.request

# 1. Auto-download the modern model file if it doesn't exist locally
MODEL_PATH = 'hand_landmarker.task'
if not os.path.exists(MODEL_PATH):
    print("Downloading MediaPipe model...")
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    urllib.request.urlretrieve(url, MODEL_PATH)

# 2. Setup Modern MediaPipe Tasks API
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=2)
detector = vision.HandLandmarker.create_from_options(options)

# 3. Setup Data Collection Variables
DATA_PATH = os.path.join('MP_Data') 
actions = np.array(['Hello', 'Namaste', 'Thank You'])
no_sequences = 30
sequence_length = 30

# Create folders for the data safely
for action in actions: 
    for sequence in range(no_sequences):
        os.makedirs(os.path.join(DATA_PATH, action, str(sequence)), exist_ok=True)

# 4. Helper function to extract keypoints for the Neural Network
def extract_keypoints(detection_result):
    hand1 = np.zeros(21 * 3)
    hand2 = np.zeros(21 * 3)
    
    if detection_result.hand_landmarks:
        hand1 = np.array([[res.x, res.y, res.z] for res in detection_result.hand_landmarks[0]]).flatten()
        if len(detection_result.hand_landmarks) > 1:
            hand2 = np.array([[res.x, res.y, res.z] for res in detection_result.hand_landmarks[1]]).flatten()
            
    return np.concatenate([hand1, hand2])

# 5. Helper function to draw skeleton manually using OpenCV
HAND_CONNECTIONS = [
    (0,1), (1,2), (2,3), (3,4), (0,5), (5,6), (6,7), (7,8),
    (5,9), (9,10), (10,11), (11,12), (9,13), (13,14), (14,15), (15,16),
    (13,17), (0,17), (17,18), (18,19), (19,20)
]

def draw_landmarks(image, hand_landmarks):
    h, w, c = image.shape
    # Draw lines
    for connection in HAND_CONNECTIONS:
        pt1 = hand_landmarks[connection[0]]
        pt2 = hand_landmarks[connection[1]]
        cv2.line(image, (int(pt1.x * w), int(pt1.y * h)), (int(pt2.x * w), int(pt2.y * h)), (13, 148, 136), 2)
    # Draw joints
    for lm in hand_landmarks:
        cv2.circle(image, (int(lm.x * w), int(lm.y * h)), 4, (0, 0, 255), -1)

# 6. Main Capture Loop
cap = cv2.VideoCapture(0)

for action in actions:
    for sequence in range(no_sequences):
        for frame_num in range(sequence_length):
            ret, frame = cap.read()
            frame = cv2.flip(frame, 1)
            
            # Format image for Tasks API
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Detect Hands
            results = detector.detect(mp_image)
            
            # Draw Landmarks on the video feed
            if results.hand_landmarks:
                for hand_lms in results.hand_landmarks:
                    draw_landmarks(frame, hand_lms)
            
            # UI text and Pauses
            if frame_num == 0: 
                cv2.putText(frame, 'STARTING COLLECTION', (120,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255, 0), 4, cv2.LINE_AA)
                cv2.putText(frame, f'Collecting {action} - Video {sequence}', (15,25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                cv2.imshow('SIH 2026 Data Collection', frame)
                cv2.waitKey(2000) # 2-second pause to get ready
            else: 
                cv2.putText(frame, f'Collecting {action} - Video {sequence}', (15,25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                cv2.imshow('SIH 2026 Data Collection', frame)
            
            # Extract and save coordinate math
            keypoints = extract_keypoints(results)
            npy_path = os.path.join(DATA_PATH, action, str(sequence), str(frame_num))
            np.save(npy_path, keypoints)
            
            # Press 'q' to gracefully quit early if needed
            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

cap.release()
cv2.destroyAllWindows()