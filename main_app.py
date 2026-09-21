import os
import cv2
import numpy as np
import base64
import urllib.request
import datetime
import jwt
import bcrypt
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ==========================================
# 1. MONGODB & AUTHENTICATION SETUP
# ==========================================
MONGO_URL = "mongodb+srv://sayan2008c_db_user:IoeLEYRREtrqTnmS@cluster0.njngnoe.mongodb.net/?appName=Cluster0"
client = AsyncIOMotorClient(MONGO_URL)
db = client.sih_database 

SECRET_KEY = "sih2026_super_secret_key" 

class UserRegister(BaseModel):
    name: str
    age: int
    mobile: str
    email: str
    password: str

class UserLogin(BaseModel):
    identifier: str
    password: str

class UserUpdate(BaseModel):
    original_email: str
    current_password: str
    name: str
    age: int
    mobile: str
    email: str

class PasswordChange(BaseModel):
    email: str
    current_password: str
    new_password: str

class ChatSave(BaseModel):
    email: str
    mode_used: str
    transcript: str

# ==========================================
# 2. MEDIAPIPE AI SETUP
# ==========================================
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
MODEL_PATH = "gesture_recognizer.task"

if not os.path.exists(MODEL_PATH):
    print("Downloading pre-trained gesture model...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.GestureRecognizerOptions(
    base_options=base_options, 
    num_hands=1,
    min_hand_detection_confidence=0.85,
    min_hand_presence_confidence=0.85,
    min_tracking_confidence=0.85
)
recognizer = vision.GestureRecognizer.create_from_options(options)

gesture_map = {
    "Thumb_Up": "👍 Good / Yes", "Thumb_Down": "👎 Bad / No",
    "Victory": "✌️ Victory / Two", "Open_Palm": "✋ Wait / Stop",
    "Closed_Fist": "✊ Solid / Fist", "ILoveYou": "🤟 I Love You",
    "Pointing_Up": "☝️ Up / One", "PointingAtUser": "🫵🏻 Pointing at You",
    "Call_Me": "🤙 Call Me", "Rock_On": "🤘 Rock On",
    "Fist_Bump": "👊🏻 Fist Bump", "High_Five": "🖐 High Five",
    "PinchedHand": "🤌🏻 Pinched Hand", "Pinching": "🤏 Pinching",
    "PinchedFingers": "🫰🏻 Pinched Fingers", "None": "Sign not recognized..."
}

# ==========================================
# 3. FASTAPI SERVER & ROUTING
# ==========================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "Active", "message": "TheHomoSapiens API is running securely!"}

@app.post("/api/register")
async def register_user(user: UserRegister):
    existing_user = await db.users.find_one({"$or": [{"email": user.email}, {"mobile": user.mobile}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email or Mobile is already registered.")
    
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt).decode('utf-8')
    
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    user_dict["created_at"] = datetime.datetime.utcnow()
    
    await db.users.insert_one(user_dict)
    return {"message": "User registered successfully!"}

@app.post("/api/login")
async def login_user(user: UserLogin):
    db_user = await db.users.find_one({"$or": [{"email": user.identifier}, {"mobile": user.identifier}]})
    
    if not db_user or not bcrypt.checkpw(user.password.encode('utf-8'), db_user["password"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email/mobile or password.")
    
    token = jwt.encode({"email": db_user["email"], "name": db_user["name"]}, SECRET_KEY, algorithm="HS256")
    return {"token": token, "name": db_user["name"], "email": db_user["email"]}

@app.get("/api/user/{email}")
async def get_user_details(email: str):
    db_user = await db.users.find_one({"email": email})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"name": db_user["name"], "age": db_user["age"], "mobile": db_user["mobile"], "email": db_user["email"]}

@app.post("/api/update_user")
async def update_user(update_data: UserUpdate):
    db_user = await db.users.find_one({"email": update_data.original_email})
    
    if not db_user or not bcrypt.checkpw(update_data.current_password.encode('utf-8'), db_user["password"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Authentication failed. Incorrect current password.")
    
    if update_data.email != update_data.original_email:
        if await db.users.find_one({"email": update_data.email}):
            raise HTTPException(status_code=400, detail="New email is already in use by another account.")

    update_dict = {
        "name": update_data.name,
        "age": update_data.age,
        "mobile": update_data.mobile,
        "email": update_data.email
    }
    
    await db.users.update_one({"email": update_data.original_email}, {"$set": update_dict})
    
    if update_data.email != update_data.original_email:
        await db.conversations.update_many({"email": update_data.original_email}, {"$set": {"email": update_data.email}})
        
    return {"message": "Profile updated successfully!", "new_email": update_data.email, "new_name": update_data.name}

@app.post("/api/change_password")
async def change_password(data: PasswordChange):
    db_user = await db.users.find_one({"email": data.email})
    
    if not db_user or not bcrypt.checkpw(data.current_password.encode('utf-8'), db_user["password"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Incorrect current password.")
    
    salt = bcrypt.gensalt()
    hashed_new_password = bcrypt.hashpw(data.new_password.encode('utf-8'), salt).decode('utf-8')
    
    await db.users.update_one({"email": data.email}, {"$set": {"password": hashed_new_password}})
    return {"message": "Password updated successfully!"}

@app.post("/api/save_chat")
async def save_chat(chat: ChatSave):
    chat_dict = chat.dict()
    chat_dict["timestamp"] = datetime.datetime.utcnow()
    await db.conversations.insert_one(chat_dict)
    return {"message": "Saved"}

@app.get("/api/history/{email}")
async def get_history(email: str):
    cursor = db.conversations.find({"email": email}).sort("timestamp", -1)
    history = await cursor.to_list(length=50)
    for item in history:
        item["_id"] = str(item["_id"]) 
        if "timestamp" in item:
            item["timestamp"] = item["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return {"history": history}

@app.websocket("/ws/translate")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            header, encoded = data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None: continue

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            
            # --- CRITICAL LATENCY FIX: Offload heavy AI to background thread ---
            recognition_result = await asyncio.to_thread(recognizer.recognize, mp_image)
            
            response = {"translation": "No hand detected", "landmarks": []}
            
            if recognition_result.hand_landmarks:
                landmarks = recognition_result.hand_landmarks[0]
                response["landmarks"] = [{"x": lm.x, "y": lm.y, "z": lm.z} for lm in landmarks]
                if recognition_result.gestures and len(recognition_result.gestures[0]) > 0:
                    top_gesture = recognition_result.gestures[0][0].category_name
                    response["translation"] = gesture_map.get(top_gesture, "Sign not recognized...") if top_gesture not in ["", "None"] else "Sign not recognized..."
            
            await websocket.send_json(response)
    except WebSocketDisconnect:
        pass