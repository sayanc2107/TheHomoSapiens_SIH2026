import os
import uuid
import datetime
import jwt
import bcrypt
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

# ==========================================
# 1. DATABASE & CONFIGURATION
# ==========================================
MONGO_URL = "mongodb+srv://sayan2008c_db_user:IoeLEYRREtrqTnmS@cluster0.njngnoe.mongodb.net/?appName=Cluster0"
client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
db = client.sih_database

SECRET_KEY = "sih2026_super_secret_key_isl_12345"

class UserRegister(BaseModel):
    name: str
    dob: str
    email: str
    mobile: str
    password: str
    profile_picture: Optional[str] = ""

class UserLogin(BaseModel):
    identifier: str
    password: str

class PasswordReset(BaseModel):
    identifier: str
    new_password: str

class UserUpdate(BaseModel):
    original_email: str
    current_password: str
    name: str
    dob: str
    mobile: str
    email: str
    profile_picture: Optional[str] = ""

class PasswordChange(BaseModel):
    email: str
    current_password: str
    new_password: str

class ChatSave(BaseModel):
    email: str
    mode_used: str 
    transcript: str

class HistoryClearRequest(BaseModel):
    email: str
    item_id: Optional[str] = None 

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

# ==========================================
# 2. FASTAPI SERVER & APIS
# ==========================================
app = FastAPI(title="TheHomoSapiens SIH 2026 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "Active", "message": "TheHomoSapiens Backend is awake!"}

@app.post("/api/register")
async def register(user: UserRegister):
    existing = await db.users.find_one({"$or": [{"email": user.email}, {"mobile": user.mobile}]})
    if existing:
        raise HTTPException(status_code=400, detail="Email or Mobile is already registered.")
    
    hashed = await asyncio.to_thread(hash_password, user.password)
    user_dict = user.dict()
    user_dict["unique_id"] = f"THS-{str(uuid.uuid4())[:8].upper()}"
    user_dict["password"] = hashed
    user_dict["created_at"] = datetime.datetime.utcnow()
    
    await db.users.insert_one(user_dict)
    return {"message": "Account created successfully!"}

@app.post("/api/login")
async def login(credentials: UserLogin):
    db_user = await db.users.find_one({"$or": [{"email": credentials.identifier}, {"mobile": credentials.identifier}]})
    if not db_user:
        raise HTTPException(status_code=401, detail="Account not found. Please register.")
    
    is_valid = await asyncio.to_thread(verify_password, credentials.password, db_user["password"])
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid password.")
    
    token = jwt.encode({"email": db_user["email"], "name": db_user["name"]}, SECRET_KEY, algorithm="HS256")
    return {
        "token": token,
        "unique_id": db_user.get("unique_id", "THS-USER"),
        "name": db_user["name"],
        "email": db_user["email"],
        "dob": db_user.get("dob", ""),
        "mobile": db_user["mobile"],
        "profile_picture": db_user.get("profile_picture", "")
    }

@app.post("/api/reset_password")
async def reset_password(data: PasswordReset):
    db_user = await db.users.find_one({"$or": [{"email": data.identifier}, {"mobile": data.identifier}]})
    if not db_user:
        raise HTTPException(status_code=404, detail="Account does not exist.")
    
    hashed = await asyncio.to_thread(hash_password, data.new_password)
    await db.users.update_one({"_id": db_user["_id"]}, {"$set": {"password": hashed}})
    return {"message": "Password reset successfully. Please log in."}

@app.get("/api/user/{email}")
async def get_user_profile(email: str):
    db_user = await db.users.find_one({"email": email})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {
        "unique_id": db_user.get("unique_id", "THS-USER"),
        "name": db_user["name"],
        "dob": db_user.get("dob", ""),
        "mobile": db_user["mobile"],
        "email": db_user["email"],
        "profile_picture": db_user.get("profile_picture", "")
    }

@app.post("/api/update_user")
async def update_profile(data: UserUpdate):
    db_user = await db.users.find_one({"email": data.original_email})
    is_valid = await asyncio.to_thread(verify_password, data.current_password, db_user["password"])
    if not is_valid:
        raise HTTPException(status_code=401, detail="Authentication failed. Incorrect current password.")
    
    if data.email != data.original_email:
        if await db.users.find_one({"email": data.email}):
            raise HTTPException(status_code=400, detail="New email already used.")
            
    updates = {"name": data.name, "dob": data.dob, "mobile": data.mobile, "email": data.email, "profile_picture": data.profile_picture}
    await db.users.update_one({"email": data.original_email}, {"$set": updates})
    
    if data.email != data.original_email:
        await db.conversations.update_many({"email": data.original_email}, {"$set": {"email": data.email}})
        
    return {"message": "Profile updated successfully!", "new_name": data.name, "new_email": data.email, "new_dob": data.dob, "new_mobile": data.mobile, "new_profile_picture": data.profile_picture}

@app.post("/api/change_password")
async def change_password(data: PasswordChange):
    db_user = await db.users.find_one({"email": data.email})
    is_valid = await asyncio.to_thread(verify_password, data.current_password, db_user["password"])
    if not is_valid:
        raise HTTPException(status_code=401, detail="Incorrect current password.")
        
    hashed = await asyncio.to_thread(hash_password, data.new_password)
    await db.users.update_one({"email": data.email}, {"$set": {"password": hashed}})
    return {"message": "Password updated successfully!"}

@app.post("/api/save_chat")
async def save_chat(chat: ChatSave):
    db_user = await db.users.find_one({"email": chat.email})
    user_uid = db_user.get("unique_id", "THS-USER") if db_user else "THS-USER"
    
    doc = {
        "unique_id": user_uid,
        "email": chat.email,
        "mode_used": chat.mode_used,
        "transcript": chat.transcript,
        "timestamp": datetime.datetime.utcnow()
    }
    await db.conversations.insert_one(doc)
    return {"message": "Conversation saved."}

@app.get("/api/history/{email}")
async def fetch_history(email: str):
    cursor = db.conversations.find({"email": email}).sort("timestamp", -1)
    records = await cursor.to_list(length=200)
    history = [{"id": str(r["_id"]), "unique_id": r.get("unique_id", "THS-USER"), "mode_used": r.get("mode_used", "General"), "transcript": r.get("transcript", ""), "timestamp": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S")} for r in records]
    return {"history": history}

@app.post("/api/clear_history")
async def clear_history(req: HistoryClearRequest):
    from bson import ObjectId
    if req.item_id:
        await db.conversations.delete_one({"_id": ObjectId(req.item_id), "email": req.email})
    else:
        await db.conversations.delete_many({"email": req.email})
    return {"message": "History cleared."}