import cv2
import mediapipe as mp
import numpy as np
import os
import time

# 1. Setup MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5, max_num_hands=2)

# 2. Setup Data Collection Variables
DATA_PATH = os.path.join('MP_Data') 
actions = np.array(['Hello', 'Namaste', 'Thank You']) # Start with 3 words to test
no_sequences = 30  # How many times you will perform each sign
sequence_length = 30  # How many frames each sequence lasts

# 3. Create Folders for the data
for action in actions: 
    for sequence in range(no_sequences):
        try: 
            os.makedirs(os.path.join(DATA_PATH, action, str(sequence)))
        except:
            pass

# 4. Helper function to extract and format the coordinates
def extract_keypoints(results):
    hand1 = np.zeros(21 * 3)
    hand2 = np.zeros(21 * 3)
    
    if results.multi_hand_landmarks:
        # Get first hand
        hand1 = np.array([[res.x, res.y, res.z] for res in results.multi_hand_landmarks[0].landmark]).flatten()
        # If there is a second hand, get it too
        if len(results.multi_hand_landmarks) > 1:
            hand2 = np.array([[res.x, res.y, res.z] for res in results.multi_hand_landmarks[1].landmark]).flatten()
            
    return np.concatenate([hand1, hand2]) # Returns a flat array of 126 values

# 5. Main Capture Loop
cap = cv2.VideoCapture(0)

for action in actions:
    for sequence in range(no_sequences):
        for frame_num in range(sequence_length):
            
            ret, frame = cap.read()
            frame = cv2.flip(frame, 1) # Mirror image
            
            # Convert BGR to RGB for MediaPipe
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = hands.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            # Draw landmarks on the screen
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Collection Logic & UI
            if frame_num == 0: 
                cv2.putText(image, 'STARTING COLLECTION', (120,200), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255, 0), 4, cv2.LINE_AA)
                cv2.putText(image, f'Collecting frames for {action} Video Number {sequence}', (15,12), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
                cv2.imshow('OpenCV Feed', image)
                cv2.waitKey(2000) # Give yourself 2 seconds to get ready before recording starts
            else: 
                cv2.putText(image, f'Collecting frames for {action} Video Number {sequence}', (15,12), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
                cv2.imshow('OpenCV Feed', image)
            
            # Extract keypoints and save them to a .npy file
            keypoints = extract_keypoints(results)
            npy_path = os.path.join(DATA_PATH, action, str(sequence), str(frame_num))
            np.save(npy_path, keypoints)
            
            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

cap.release()
cv2.destroyAllWindows()