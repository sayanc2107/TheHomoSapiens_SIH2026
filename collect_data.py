import cv2
import numpy as np
import os
import mediapipe as mp
import time

# Initialize MediaPipe Holistic and Drawing utilities
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

# The exact vocabulary list from your notes (duplicates removed)
actions = np.array([
    'Hello', 'Namaste', 'Thank You', 'Please', 'Sorry', 'Welcome', 'Good', 'Bad', 'Yes', 'No', 
    'I_Me', 'You', 'We', 'He', 'She', 'Friend', 'Teacher', 'Student', 'Mother', 'Father', 
    'Name', 'What', 'Where', 'Who', 'Why', 'How', 'Want', 'Need', 'Know', 'Understand', 
    'Dont know', 'Help', 'Wait', 'Come', 'Go', 'Water', 'Food', 'Eat', 'Drink', 'Home', 
    'Bathroom', 'Medicine', 'Hospital', 'Sleep', 'Work', 'College', 'Class', 'Book', 
    'Computer', 'Exam', 'Learn', 'Study', 'Question', 'Answer', 'Happy', 'Sad', 'Love', 
    'Like', 'Good Morning', 'Good Afternoon', 'Good Evening', 'Good night'
])

# Configuration
DATA_PATH = os.path.join('ISL_Dataset')
no_sequences = 30    # Number of videos to record per word
sequence_length = 30 # Number of frames per video

# Create directory structure
for action in actions: 
    for sequence in range(no_sequences):
        try: 
            os.makedirs(os.path.join(DATA_PATH, action, str(sequence)))
        except:
            pass

def extract_keypoints(results):
    """Extracts and flattens pose and hand landmarks into a single array."""
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in results.pose_landmarks.landmark]).flatten() if results.pose_landmarks else np.zeros(33*4)
    lh = np.array([[res.x, res.y, res.z] for res in results.left_hand_landmarks.landmark]).flatten() if results.left_hand_landmarks else np.zeros(21*3)
    rh = np.array([[res.x, res.y, res.z] for res in results.right_hand_landmarks.landmark]).flatten() if results.right_hand_landmarks else np.zeros(21*3)
    return np.concatenate([pose, lh, rh])

cap = cv2.VideoCapture(0)

with mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5) as holistic:
    for action in actions:
        for sequence in range(no_sequences):
            for frame_num in range(sequence_length):

                ret, frame = cap.read()
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = holistic.process(image)
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                # Draw landmarks on the live feed
                mp_drawing.draw_landmarks(image, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                mp_drawing.draw_landmarks(image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

                # Collection UI Prompts
                if frame_num == 0:
                    cv2.putText(image, 'STARTING COLLECTION', (120,200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255, 0), 4, cv2.LINE_AA)
                    cv2.putText(image, f'Collecting frames for {action} Video Number {sequence}', (15,12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
                    cv2.imshow('ISL Data Collection', image)
                    cv2.waitKey(2000) # 2-second break between videos to reset hands
                else: 
                    cv2.putText(image, f'Collecting frames for {action} Video Number {sequence}', (15,12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
                    cv2.imshow('ISL Data Collection', image)

                # Extract and save data
                keypoints = extract_keypoints(results)
                npy_path = os.path.join(DATA_PATH, action, str(sequence), str(frame_num))
                np.save(npy_path, keypoints)

                # Break gracefully if 'q' is pressed
                if cv2.waitKey(10) & 0xFF == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    exit()
                    
cap.release()
cv2.destroyAllWindows()