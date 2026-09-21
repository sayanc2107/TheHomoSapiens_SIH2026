import os
import cv2
import numpy as np
import base64
import urllib.request
import datetime
import jwt
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ==========================================
# 1. MONGODB & AUTHENTICATION SETUP
# ==========================================
# Connecting to your local MongoDB Compass instance
MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client.sih_database # The database will automatically be created in Compass

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "sih2026_super_secret_key" # Change this before actual production

# Pydantic Models for incoming JSON requests
class UserRegister(BaseModel):
    name: str
    age: int
    mobile: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class ChatSave(BaseModel):
    email: str
    mode_used: str
    transcript: str

# ==========================================
# 2. MEDIAPIPE AI SETUP
# ==========================================
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
MODEL_PATH = "gesture_recognizer.task"

# Download the pre-trained model if it doesn't exist locally
if not os.path.exists(MODEL_PATH):
    print("Downloading pre-trained gesture model...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

# Initialize the Gesture Recognizer API with STRICT thresholds (85%)
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.GestureRecognizerOptions(
    base_options=base_options, 
    num_hands=1,
    min_hand_detection_confidence=0.85,
    min_hand_presence_confidence=0.85,
    min_tracking_confidence=0.85
)
recognizer = vision.GestureRecognizer.create_from_options(options)

# Expanded Gesture Dictionary
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

# ==========================================
# 3. FASTAPI SERVER & ROUTING
# ==========================================
app = FastAPI()

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Active", "message": "TheHomoSapiens SIH 2026 Backend is running with MongoDB."}

# --- REST APIs FOR USER ACCOUNTS ---

@app.post("/api/register")
async def register_user(user: UserRegister):
    # Check if email is already in the database
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")
    
    # Hash password and save the new user
    hashed_password = pwd_context.hash(user.password)
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    user_dict["created_at"] = datetime.datetime.utcnow()
    
    await db.users.insert_one(user_dict)
    return {"message": "User registered successfully!"}

@app.post("/api/login")
async def login_user(user: UserLogin):
    # Find user by email
    db_user = await db.users.find_one({"email": user.email})
    
    # Verify user exists and password is correct
    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    
    # Generate a JWT token for the frontend
    token = jwt.encode({"email": user.email, "name": db_user["name"]}, SECRET_KEY, algorithm="HS256")
    return {"token": token, "name": db_user["name"], "email": db_user["email"]}

# --- REST APIs FOR SAVING & LOADING DATA ---

@app.post("/api/save_chat")
async def save_chat(chat: ChatSave):
    chat_dict = chat.dict()
    chat_dict["timestamp"] = datetime.datetime.utcnow()
    # Save the translation log to the 'conversations' collection
    await db.conversations.insert_one(chat_dict)
    return {"message": "Conversation securely saved to database."}

@app.get("/api/history/{email}")
async def get_history(email: str):
    # Retrieve top 50 recent conversations for this specific user
    cursor = db.conversations.find({"email": email}).sort("timestamp", -1)
    history = await cursor.to_list(length=50)
    
    # MongoDB '_id' must be converted to a string before sending via JSON
    for item in history:
        item["_id"] = str(item["_id"]) 
        # Format the datetime nicely for the frontend
        if "timestamp" in item:
            item["timestamp"] = item["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            
    return {"history": history}

# --- WEBSOCKET FOR LIVE CAMERA TRANSLATION ---

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
            
            # Process the image with the AI model
            recognition_result = recognizer.recognize(mp_image)
            
            response = {
                "translation": "No hand detected",
                "landmarks": []
            }
            
            # Extract landmarks and gesture classification if hand is found
            if recognition_result.hand_landmarks:
                landmarks = recognition_result.hand_landmarks[0]
                response["landmarks"] = [{"x": lm.x, "y": lm.y, "z": lm.z} for lm in landmarks]
                
                if recognition_result.gestures and len(recognition_result.gestures[0]) > 0:
                    top_gesture = recognition_result.gestures[0][0].category_name
                    
                    if top_gesture == "" or top_gesture == "None":
                        response["translation"] = "Sign not recognized..."
                    else:
                        response["translation"] = gesture_map.get(top_gesture, "Sign not recognized...")
                else:
                    response["translation"] = "Sign not recognized..."
            
            # Send the result back to the frontend
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"WebSocket Error: {e}")