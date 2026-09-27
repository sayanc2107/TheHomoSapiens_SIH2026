import os
import uuid
import datetime
import time
import jwt
import bcrypt
import asyncio
import platform
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Header, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# ==========================================
# 1. DATABASE & CONFIGURATION
# ==========================================
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://sayan2008c_db_user:IoeLEYRREtrqTnmS@cluster0.njngnoe.mongodb.net/?appName=Cluster0")

class DatabaseProxy:
    _clients = {}

    def _get_db(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        loop_id = id(loop) if loop else 0
        if loop_id not in self._clients:
            self._clients[loop_id] = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000).sih_database
        return self._clients[loop_id]

    def __getattr__(self, name):
        return getattr(self._get_db(), name)

    def __getitem__(self, name):
        return self._get_db()[name]

db = DatabaseProxy()

SECRET_KEY = os.getenv("SECRET_KEY", "sih2026_super_secret_key_isl_12345")
SERVER_START_TIME = datetime.datetime.now(datetime.timezone.utc)

# ==========================================
# 2. MODELS & SCHEMAS
# ==========================================
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

# Admin Specific Models
class AdminLoginRequest(BaseModel):
    identifier: str
    password: str

class AdminUserCreate(BaseModel):
    name: str
    email: str
    mobile: str
    dob: Optional[str] = ""
    password: str
    role: Optional[str] = "user" # user, admin, manager
    status: Optional[str] = "active" # active, suspended
    profile_picture: Optional[str] = ""

class AdminUserUpdate(BaseModel):
    name: str
    mobile: str
    dob: Optional[str] = ""
    email: str
    role: Optional[str] = "user"
    status: Optional[str] = "active"
    profile_picture: Optional[str] = ""

class AdminPasswordReset(BaseModel):
    new_password: str

class BulkDeleteRequest(BaseModel):
    ids: Optional[List[str]] = []
    clear_all: Optional[bool] = False

class VocabItem(BaseModel):
    word: str
    category: str
    description: Optional[str] = ""
    hand_posture: Optional[str] = ""
    difficulty: Optional[str] = "Beginner" # Beginner, Intermediate, Advanced
    video_sequences: Optional[int] = 30
    status: Optional[str] = "active"

class AuditLogItem(BaseModel):
    action: str
    details: str
    performed_by: Optional[str] = "Admin"

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

async def log_audit_event(action: str, details: str, performed_by: str = "Admin"):
    try:
        await db.audit_logs.insert_one({
            "action": action,
            "details": details,
            "performed_by": performed_by,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        })
    except Exception as e:
        print(f"Audit log error: {e}")

# ==========================================
# 4. DEFAULT SEED DATA (SIH 2026 ISL ACTIONS)
# ==========================================
DEFAULT_ACTIONS = [
    {"word": "Hello", "category": "Greetings", "difficulty": "Beginner", "hand_posture": "Open hand waved near temple", "video_sequences": 30},
    {"word": "Namaste", "category": "Greetings", "difficulty": "Beginner", "hand_posture": "Both palms pressed together at chest", "video_sequences": 30},
    {"word": "Thank You", "category": "Greetings", "difficulty": "Beginner", "hand_posture": "Fingertips touch chin and move forward", "video_sequences": 30},
    {"word": "Please", "category": "Greetings", "difficulty": "Beginner", "hand_posture": "Flat palm circular motion on chest", "video_sequences": 30},
    {"word": "Sorry", "category": "Greetings", "difficulty": "Beginner", "hand_posture": "Fist rubbed in circular motion on chest", "video_sequences": 30},
    {"word": "Welcome", "category": "Greetings", "difficulty": "Beginner", "hand_posture": "Open hand sweeping inward toward torso", "video_sequences": 30},
    {"word": "Good Morning", "category": "Greetings", "difficulty": "Intermediate", "hand_posture": "Good sign followed by arm rising like sun", "video_sequences": 30},
    {"word": "Good Afternoon", "category": "Greetings", "difficulty": "Intermediate", "hand_posture": "Good sign followed by flat arm pointing midday", "video_sequences": 30},
    {"word": "Good Evening", "category": "Greetings", "difficulty": "Intermediate", "hand_posture": "Good sign followed by wrist curving down like dusk", "video_sequences": 30},
    {"word": "Good night", "category": "Greetings", "difficulty": "Intermediate", "hand_posture": "Good sign followed by arm sweeping over horizon", "video_sequences": 30},
    {"word": "Good", "category": "Feelings", "difficulty": "Beginner", "hand_posture": "Flat hand from mouth to palm", "video_sequences": 30},
    {"word": "Bad", "category": "Feelings", "difficulty": "Beginner", "hand_posture": "Flat hand turned downward sharply", "video_sequences": 30},
    {"word": "Yes", "category": "Feelings", "difficulty": "Beginner", "hand_posture": "Fist nodding up and down like head", "video_sequences": 30},
    {"word": "No", "category": "Feelings", "difficulty": "Beginner", "hand_posture": "Index and middle finger snap to thumb", "video_sequences": 30},
    {"word": "Happy", "category": "Feelings", "difficulty": "Beginner", "hand_posture": "Open hands fluttering upward on chest", "video_sequences": 30},
    {"word": "Sad", "category": "Feelings", "difficulty": "Beginner", "hand_posture": "Open palms drawn down face with somber look", "video_sequences": 30},
    {"word": "Love", "category": "Feelings", "difficulty": "Beginner", "hand_posture": "Fists crossed over heart", "video_sequences": 30},
    {"word": "Like", "category": "Feelings", "difficulty": "Beginner", "hand_posture": "Thumb and middle finger pinch pulled from chest", "video_sequences": 30},
    {"word": "I_Me", "category": "Pronouns", "difficulty": "Beginner", "hand_posture": "Index finger pointing to chest", "video_sequences": 30},
    {"word": "You", "category": "Pronouns", "difficulty": "Beginner", "hand_posture": "Index finger pointing outward to person", "video_sequences": 30},
    {"word": "We", "category": "Pronouns", "difficulty": "Beginner", "hand_posture": "Index finger circling from right to left shoulder", "video_sequences": 30},
    {"word": "He", "category": "Pronouns", "difficulty": "Beginner", "hand_posture": "Index finger pointing to male side", "video_sequences": 30},
    {"word": "She", "category": "Pronouns", "difficulty": "Beginner", "hand_posture": "Index finger pointing to female side", "video_sequences": 30},
    {"word": "Friend", "category": "Pronouns", "difficulty": "Beginner", "hand_posture": "Interlocking index fingers hooked back and forth", "video_sequences": 30},
    {"word": "Teacher", "category": "Pronouns", "difficulty": "Intermediate", "hand_posture": "Flatted O hands from forehead outward + person marker", "video_sequences": 30},
    {"word": "Student", "category": "Pronouns", "difficulty": "Intermediate", "hand_posture": "Lifting knowledge from palm to forehead + person marker", "video_sequences": 30},
    {"word": "Mother", "category": "Pronouns", "difficulty": "Beginner", "hand_posture": "Open hand with thumb tapped on chin", "video_sequences": 30},
    {"word": "Father", "category": "Pronouns", "difficulty": "Beginner", "hand_posture": "Open hand with thumb tapped on forehead", "video_sequences": 30},
    {"word": "Name", "category": "Questions", "difficulty": "Beginner", "hand_posture": "H-hands tapped crosswise twice", "video_sequences": 30},
    {"word": "What", "category": "Questions", "difficulty": "Beginner", "hand_posture": "Open hands palms up shaken slightly side to side", "video_sequences": 30},
    {"word": "Where", "category": "Questions", "difficulty": "Beginner", "hand_posture": "Index finger pointed up shaken side to side", "video_sequences": 30},
    {"word": "Who", "category": "Questions", "difficulty": "Beginner", "hand_posture": "Index finger circled around mouth", "video_sequences": 30},
    {"word": "Why", "category": "Questions", "difficulty": "Beginner", "hand_posture": "Hand from forehead pulling down into Y shape", "video_sequences": 30},
    {"word": "How", "category": "Questions", "difficulty": "Beginner", "hand_posture": "Cupped hands back-to-back rotated upward", "video_sequences": 30},
    {"word": "Question", "category": "Questions", "difficulty": "Intermediate", "hand_posture": "Index finger drawing question mark in air", "video_sequences": 30},
    {"word": "Answer", "category": "Questions", "difficulty": "Intermediate", "hand_posture": "Index fingers pointing outward from chin simultaneously", "video_sequences": 30},
    {"word": "Want", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Cupped hands pulled toward body", "video_sequences": 30},
    {"word": "Need", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Bent X finger moved downward assertively", "video_sequences": 30},
    {"word": "Know", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Fingertips tapped on temple", "video_sequences": 30},
    {"word": "Understand", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Fist next to temple with index finger flicking up", "video_sequences": 30},
    {"word": "Dont know", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Hand touched to temple and waved outward with shrug", "video_sequences": 30},
    {"word": "Help", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Fist with thumb up on flat palm, lifted together", "video_sequences": 30},
    {"word": "Wait", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Open hands with wiggling fingers held forward", "video_sequences": 30},
    {"word": "Come", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Index fingers beckoning toward chest", "video_sequences": 30},
    {"word": "Go", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Index fingers arcing forward away from body", "video_sequences": 30},
    {"word": "Eat", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Squashed O-hand tapped at mouth", "video_sequences": 30},
    {"word": "Drink", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "C-hand tilted upward toward mouth like a cup", "video_sequences": 30},
    {"word": "Sleep", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Open hand drawn down face closing into fist", "video_sequences": 30},
    {"word": "Work", "category": "Daily Actions", "difficulty": "Beginner", "hand_posture": "Fist tapped on top of other fist wrist", "video_sequences": 30},
    {"word": "Water", "category": "Essentials", "difficulty": "Beginner", "hand_posture": "W-hand tapped on chin", "video_sequences": 30},
    {"word": "Food", "category": "Essentials", "difficulty": "Beginner", "hand_posture": "Fingertips brought to mouth repeatedly", "video_sequences": 30},
    {"word": "Home", "category": "Essentials", "difficulty": "Beginner", "hand_posture": "Flattened O-hand touches cheek then jaw", "video_sequences": 30},
    {"word": "Bathroom", "category": "Essentials", "difficulty": "Beginner", "hand_posture": "T-hand shaken side to side", "video_sequences": 30},
    {"word": "Medicine", "category": "Essentials", "difficulty": "Intermediate", "hand_posture": "Middle finger rubbed in palm circular motion", "video_sequences": 30},
    {"word": "Hospital", "category": "Essentials", "difficulty": "Intermediate", "hand_posture": "H-hand tracing a cross on upper arm", "video_sequences": 30},
    {"word": "College", "category": "Education", "difficulty": "Intermediate", "hand_posture": "Flat hand slides off palm and arcs upward", "video_sequences": 30},
    {"word": "Class", "category": "Education", "difficulty": "Intermediate", "hand_posture": "C-hands starting together and circling outward into a group", "video_sequences": 30},
    {"word": "Book", "category": "Education", "difficulty": "Beginner", "hand_posture": "Palms together opening outward like a book", "video_sequences": 30},
    {"word": "Computer", "category": "Education", "difficulty": "Intermediate", "hand_posture": "C-hand arcing up along forearm", "video_sequences": 30},
    {"word": "Exam", "category": "Education", "difficulty": "Intermediate", "hand_posture": "Both hands pointing down with test-paper motion", "video_sequences": 30},
    {"word": "Learn", "category": "Education", "difficulty": "Beginner", "hand_posture": "Taking idea from palm up to forehead", "video_sequences": 30},
    {"word": "Study", "category": "Education", "difficulty": "Beginner", "hand_posture": "Fingers wiggling at flat palm", "video_sequences": 30}
]

# ==========================================
# 5. FASTAPI SERVER & APIS
# ==========================================
app = FastAPI(title="TheHomoSapiens SIH 2026 API & Admin Suite")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_init():
    try:
        # 1. Clean up legacy admin account if present
        await db.users.delete_many({"email": "admin@homosapiens.ai"})

        # 2. Ensure sayan@superadmin.com is configured as Super Admin
        admin = await db.users.find_one({"email": "sayan@superadmin.com"})
        if not admin:
            hashed = await asyncio.to_thread(hash_password, "SuperAdmin@123")
            await db.users.insert_one({
                "name": "Sayan Chakraborty",
                "email": "sayan@superadmin.com",
                "mobile": "9876543210",
                "dob": "2004-01-01",
                "password": hashed,
                "role": "superadmin",
                "status": "active",
                "unique_id": "THS-SUPERADMIN",
                "profile_picture": "https://ui-avatars.com/api/?name=Sayan+SuperAdmin&background=20263f&color=7ae2d5",
                "created_at": datetime.datetime.now(datetime.timezone.utc)
            })
            print("[INFO] Super Admin initialized: sayan@superadmin.com")
        else:
            await db.users.update_one(
                {"email": "sayan@superadmin.com"},
                {"$set": {"role": "superadmin", "status": "active"}}
            )

        # 3. Seed Vocabulary if empty
        vocab_count = await db.vocabulary.count_documents({})
        if vocab_count == 0:
            docs = []
            for item in DEFAULT_ACTIONS:
                doc = {**item, "status": "active", "created_at": datetime.datetime.now(datetime.timezone.utc)}
                docs.append(doc)
            if docs:
                await db.vocabulary.insert_many(docs)
                print(f"[INFO] Seeded {len(docs)} ISL vocabulary actions into database.")
    except Exception as e:
        print(f"[WARN] Startup DB setup warning: {e}")

# ==========================================
# 6. STATIC / PORTAL HTML ROUTES
# ==========================================
@app.get("/")
async def root():
    return {
        "status": "Active",
        "message": "TheHomoSapiens Backend & Admin Suite is awake!",
        "version": "2.4.0",
        "portal_url": "/portal",
        "admin_url": "/admin"
    }

@app.get("/portal")
@app.get("/index.html")
async def serve_portal():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "index.html not found"}

@app.get("/admin")
@app.get("/admin.html")
async def serve_admin():
    if os.path.exists("admin.html"):
        return FileResponse("admin.html")
    return {"message": "admin.html not found"}

# ==========================================
# 7. ORIGINAL USER PORTAL APIS
# ==========================================
@app.post("/api/register")
async def register(user: UserRegister):
    existing = await db.users.find_one({"$or": [{"email": user.email}, {"mobile": user.mobile}]})
    if existing:
        raise HTTPException(status_code=400, detail="Email or Mobile is already registered.")
    
    hashed = await asyncio.to_thread(hash_password, user.password)
    user_dict = user.dict()
    user_dict["unique_id"] = f"THS-{str(uuid.uuid4())[:8].upper()}"
    user_dict["password"] = hashed
    user_dict["role"] = "user"
    user_dict["status"] = "active"
    user_dict["created_at"] = datetime.datetime.now(datetime.timezone.utc)
    
    await db.users.insert_one(user_dict)
    await log_audit_event("User Registered", f"New user registered: {user.email}", performed_by=user.email)
    return {"message": "Account created successfully!"}

@app.post("/api/login")
async def login(credentials: UserLogin):
    db_user = await db.users.find_one({"$or": [{"email": credentials.identifier}, {"mobile": credentials.identifier}]})
    if not db_user:
        raise HTTPException(status_code=401, detail="Account not found. Please register.")
    
    if db_user.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Account is suspended. Please contact administrator.")

    is_valid = await asyncio.to_thread(verify_password, credentials.password, db_user["password"])
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid password.")
    
    role = db_user.get("role", "superadmin" if db_user.get("email") == "sayan@superadmin.com" else "user")
    redirect_url = "/admin" if role in ["superadmin", "admin", "manager"] else ""
    token = jwt.encode({
        "email": db_user["email"],
        "name": db_user["name"],
        "role": role,
        "unique_id": db_user.get("unique_id", "THS-USER")
    }, SECRET_KEY, algorithm="HS256")

    return {
        "token": token,
        "unique_id": db_user.get("unique_id", "THS-USER"),
        "name": db_user["name"],
        "email": db_user["email"],
        "dob": db_user.get("dob", ""),
        "mobile": db_user["mobile"],
        "role": role,
        "redirect_url": redirect_url,
        "profile_picture": db_user.get("profile_picture", "")
    }

@app.post("/api/reset_password")
async def reset_password(data: PasswordReset):
    db_user = await db.users.find_one({"$or": [{"email": data.identifier}, {"mobile": data.identifier}]})
    if not db_user:
        raise HTTPException(status_code=404, detail="Account does not exist.")
    
    hashed = await asyncio.to_thread(hash_password, data.new_password)
    await db.users.update_one({"_id": db_user["_id"]}, {"$set": {"password": hashed}})
    await log_audit_event("Password Reset", f"Password reset for: {db_user.get('email')}", performed_by=db_user.get("email"))
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
        "role": db_user.get("role", "user"),
        "status": db_user.get("status", "active"),
        "profile_picture": db_user.get("profile_picture", "")
    }

@app.post("/api/update_user")
async def update_profile(data: UserUpdate):
    db_user = await db.users.find_one({"email": data.original_email})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")

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
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")

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
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
    }
    await db.conversations.insert_one(doc)
    return {"message": "Conversation saved."}

@app.get("/api/history/{email}")
async def fetch_history(email: str):
    cursor = db.conversations.find({"email": email}).sort("timestamp", -1)
    records = await cursor.to_list(length=200)
    history = []
    for r in records:
        ts = r.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, datetime.datetime) else str(ts)
        history.append({
            "id": str(r["_id"]),
            "unique_id": r.get("unique_id", "THS-USER"),
            "mode_used": r.get("mode_used", "General"),
            "transcript": r.get("transcript", ""),
            "timestamp": ts_str
        })
    return {"history": history}

@app.post("/api/clear_history")
async def clear_history(req: HistoryClearRequest):
    if req.item_id:
        await db.conversations.delete_one({"_id": ObjectId(req.item_id), "email": req.email})
    else:
        await db.conversations.delete_many({"email": req.email})
    return {"message": "History cleared."}


# ==========================================
# 8. ADMIN SUITE APIS
# ==========================================

@app.post("/api/admin/login")
async def admin_login(creds: AdminLoginRequest):
    """Secure login endpoint specifically for Admin Panel users."""
    db_user = await db.users.find_one({"$or": [{"email": creds.identifier}, {"mobile": creds.identifier}]})
    if not db_user:
        raise HTTPException(status_code=401, detail="Admin account not found.")

    is_valid = await asyncio.to_thread(verify_password, creds.password, db_user["password"])
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")

    role = db_user.get("role", "superadmin" if db_user["email"] == "sayan@superadmin.com" else "user")
    if role not in ["superadmin", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Access denied. Administrator privileges required.")

    if db_user.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Admin account is suspended.")

    token = jwt.encode({
        "email": db_user["email"],
        "name": db_user["name"],
        "role": role,
        "unique_id": db_user.get("unique_id", "THS-ADMIN")
    }, SECRET_KEY, algorithm="HS256")

    await log_audit_event("Admin Login", f"Admin logged in: {db_user['email']}", performed_by=db_user["email"])

    return {
        "token": token,
        "name": db_user["name"],
        "email": db_user["email"],
        "role": role,
        "unique_id": db_user.get("unique_id", "THS-ADMIN"),
        "profile_picture": db_user.get("profile_picture", "")
    }

@app.get("/api/admin/stats")
async def get_admin_dashboard_stats():
    """Returns real-time KPI metrics, trends, and recent records."""
    t0 = time.time()
    try:
        await db.command("ping")
        ping_ms = round((time.time() - t0) * 1000, 2)
    except Exception:
        ping_ms = -1

    total_users = await db.users.count_documents({})
    total_convs = await db.conversations.count_documents({})
    total_vocab = await db.vocabulary.count_documents({})

    s2t_count = await db.conversations.count_documents({
        "mode_used": {"$regex": "sign|s2t", "$options": "i"}
    })
    t2s_count = await db.conversations.count_documents({
        "mode_used": {"$regex": "text|t2s|audio", "$options": "i"}
    })

    # Today's stats
    now = datetime.datetime.now(datetime.timezone.utc)
    today_start = datetime.datetime(now.year, now.month, now.day, tzinfo=datetime.timezone.utc)
    users_today = await db.users.count_documents({"created_at": {"$gte": today_start}})
    convs_today = await db.conversations.count_documents({"timestamp": {"$gte": today_start}})

    # Recent 7 days trend
    trend = []
    for i in range(6, -1, -1):
        day_date = (now - datetime.timedelta(days=i)).date()
        start = datetime.datetime(day_date.year, day_date.month, day_date.day, tzinfo=datetime.timezone.utc)
        end = start + datetime.timedelta(days=1)
        u_count = await db.users.count_documents({"created_at": {"$gte": start, "$lt": end}})
        c_count = await db.conversations.count_documents({"timestamp": {"$gte": start, "$lt": end}})
        trend.append({
            "day": day_date.strftime("%a"),
            "date": day_date.strftime("%d %b"),
            "users": u_count,
            "conversations": c_count
        })

    # Recent 5 users
    recent_users_cursor = db.users.find({}, {"password": 0}).sort("created_at", -1).limit(5)
    recent_users = []
    async for u in recent_users_cursor:
        created = u.get("created_at")
        created_str = created.strftime("%Y-%m-%d %H:%M") if isinstance(created, datetime.datetime) else str(created or "")
        recent_users.append({
            "id": str(u["_id"]),
            "name": u.get("name", "User"),
            "email": u.get("email", ""),
            "role": u.get("role", "user"),
            "status": u.get("status", "active"),
            "unique_id": u.get("unique_id", "THS-USER"),
            "created_at": created_str
        })

    # Recent 5 conversations
    recent_convs_cursor = db.conversations.find({}).sort("timestamp", -1).limit(5)
    recent_convs = []
    async for c in recent_convs_cursor:
        ts = c.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, datetime.datetime) else str(ts or "")
        recent_convs.append({
            "id": str(c["_id"]),
            "email": c.get("email", ""),
            "mode_used": c.get("mode_used", "General"),
            "transcript": c.get("transcript", "")[:60],
            "timestamp": ts_str
        })

    uptime_seconds = int((datetime.datetime.now(datetime.timezone.utc) - SERVER_START_TIME).total_seconds())

    return {
        "total_users": total_users,
        "total_conversations": total_convs,
        "total_vocabulary": total_vocab,
        "s2t_count": s2t_count,
        "t2s_count": t2s_count,
        "users_today": users_today,
        "convs_today": convs_today,
        "ping_ms": ping_ms,
        "uptime_seconds": uptime_seconds,
        "activity_trend": trend,
        "recent_users": recent_users,
        "recent_convs": recent_convs
    }

@app.get("/api/admin/users")
async def list_admin_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50
):
    """Paginated and searchable user management endpoint."""
    query: Dict[str, Any] = {}
    if search:
        s = search.strip()
        query["$or"] = [
            {"name": {"$regex": s, "$options": "i"}},
            {"email": {"$regex": s, "$options": "i"}},
            {"mobile": {"$regex": s, "$options": "i"}},
            {"unique_id": {"$regex": s, "$options": "i"}}
        ]
    if role and role != "all":
        query["role"] = role
    if status and status != "all":
        query["status"] = status

    total = await db.users.count_documents(query)
    cursor = db.users.find(query, {"password": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit)
    
    users = []
    async for u in cursor:
        user_email = u.get("email", "")
        conv_count = await db.conversations.count_documents({"email": user_email})
        created = u.get("created_at")
        created_str = created.strftime("%Y-%m-%d %H:%M") if isinstance(created, datetime.datetime) else str(created or "N/A")
        users.append({
            "id": str(u["_id"]),
            "unique_id": u.get("unique_id", "THS-USER"),
            "name": u.get("name", ""),
            "email": user_email,
            "mobile": u.get("mobile", ""),
            "dob": u.get("dob", ""),
            "role": u.get("role", "user"),
            "status": u.get("status", "active"),
            "profile_picture": u.get("profile_picture", ""),
            "created_at": created_str,
            "conversations_count": conv_count
        })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "users": users
    }

@app.post("/api/admin/users")
async def create_user_by_admin(data: AdminUserCreate):
    """Admin creates a new user account directly."""
    existing = await db.users.find_one({"$or": [{"email": data.email}, {"mobile": data.mobile}]})
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email or mobile already exists.")

    hashed = await asyncio.to_thread(hash_password, data.password)
    user_doc = {
        "name": data.name.strip(),
        "email": data.email.strip().lower(),
        "mobile": data.mobile.strip(),
        "dob": data.dob,
        "password": hashed,
        "role": data.role if data.role in ["user", "admin", "manager"] else "user",
        "status": data.status if data.status in ["active", "suspended"] else "active",
        "unique_id": f"THS-{str(uuid.uuid4())[:8].upper()}",
        "profile_picture": data.profile_picture or f"https://ui-avatars.com/api/?name={data.name}&background=20263f&color=7ae2d5",
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }

    res = await db.users.insert_one(user_doc)
    await log_audit_event("Create User", f"Admin created user: {data.email} with role {user_doc['role']}")
    return {"message": "User created successfully", "id": str(res.inserted_id), "unique_id": user_doc["unique_id"]}

@app.get("/api/admin/users/{email_or_id}")
async def get_user_details(email_or_id: str):
    """Fetch complete user profile and their individual conversation logs."""
    query = {"$or": [{"email": email_or_id}]}
    if ObjectId.is_valid(email_or_id):
        query["$or"].append({"_id": ObjectId(email_or_id)})
    
    u = await db.users.find_one(query, {"password": 0})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    user_email = u.get("email", "")
    conv_cursor = db.conversations.find({"email": user_email}).sort("timestamp", -1).limit(50)
    convs = []
    async for c in conv_cursor:
        ts = c.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, datetime.datetime) else str(ts or "")
        convs.append({
            "id": str(c["_id"]),
            "mode_used": c.get("mode_used", "General"),
            "transcript": c.get("transcript", ""),
            "timestamp": ts_str
        })

    created = u.get("created_at")
    created_str = created.strftime("%Y-%m-%d %H:%M") if isinstance(created, datetime.datetime) else str(created or "")
    
    return {
        "id": str(u["_id"]),
        "unique_id": u.get("unique_id", "THS-USER"),
        "name": u.get("name", ""),
        "email": user_email,
        "mobile": u.get("mobile", ""),
        "dob": u.get("dob", ""),
        "role": u.get("role", "user"),
        "status": u.get("status", "active"),
        "profile_picture": u.get("profile_picture", ""),
        "created_at": created_str,
        "conversations": convs
    }

@app.put("/api/admin/users/{email_or_id}")
async def update_user_by_admin(email_or_id: str, data: AdminUserUpdate):
    """Admin updates user profile, role, or active status."""
    query = {"$or": [{"email": email_or_id}]}
    if ObjectId.is_valid(email_or_id):
        query["$or"].append({"_id": ObjectId(email_or_id)})

    target = await db.users.find_one(query)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    updates: Dict[str, Any] = {
        "name": data.name.strip(),
        "mobile": data.mobile.strip(),
        "dob": data.dob,
        "role": data.role if data.role in ["user", "admin", "manager"] else target.get("role", "user"),
        "status": data.status if data.status in ["active", "suspended"] else target.get("status", "active")
    }

    if data.profile_picture:
        updates["profile_picture"] = data.profile_picture

    if data.email != target.get("email"):
        existing = await db.users.find_one({"email": data.email})
        if existing and str(existing["_id"]) != str(target["_id"]):
            raise HTTPException(status_code=400, detail="New email address already in use.")
        updates["email"] = data.email
        await db.conversations.update_many({"email": target.get("email")}, {"$set": {"email": data.email}})

    await db.users.update_one({"_id": target["_id"]}, {"$set": updates})
    await log_audit_event("Update User", f"Admin updated user profile: {target.get('email')}")
    return {"message": "User updated successfully"}

@app.delete("/api/admin/users/{email_or_id}")
async def delete_user_by_admin(email_or_id: str, delete_conversations: bool = True):
    """Admin deletes user and optionally their conversations."""
    query = {"$or": [{"email": email_or_id}]}
    if ObjectId.is_valid(email_or_id):
        query["$or"].append({"_id": ObjectId(email_or_id)})

    target = await db.users.find_one(query)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    email = target.get("email", "")
    if email == "sayan@superadmin.com" or target.get("role") == "superadmin":
        raise HTTPException(status_code=403, detail="Protected account. The Super Administrator cannot be deleted.")
    await db.users.delete_one({"_id": target["_id"]})
    if delete_conversations and email:
        await db.conversations.delete_many({"email": email})

    await log_audit_event("Delete User", f"Admin deleted user: {email} (Cascade convs: {delete_conversations})")
    return {"message": f"User {email} deleted successfully."}

@app.post("/api/admin/users/{email_or_id}/reset-password")
async def admin_force_reset_password(email_or_id: str, data: AdminPasswordReset):
    """Admin resets a user's password without knowing old password."""
    query = {"$or": [{"email": email_or_id}]}
    if ObjectId.is_valid(email_or_id):
        query["$or"].append({"_id": ObjectId(email_or_id)})

    target = await db.users.find_one(query)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    hashed = await asyncio.to_thread(hash_password, data.new_password)
    await db.users.update_one({"_id": target["_id"]}, {"$set": {"password": hashed}})
    await log_audit_event("Admin Reset Password", f"Admin force-reset password for: {target.get('email')}")
    return {"message": "Password reset successfully"}

@app.get("/api/admin/conversations")
async def list_admin_conversations(
    search: Optional[str] = None,
    mode: Optional[str] = None,
    email: Optional[str] = None,
    page: int = 1,
    limit: int = 50
):
    """Search and filter conversation logs across all users."""
    query: Dict[str, Any] = {}
    if search:
        query["transcript"] = {"$regex": search.strip(), "$options": "i"}
    if mode and mode != "all":
        if mode == "S2T":
            query["mode_used"] = {"$regex": "sign|s2t", "$options": "i"}
        elif mode == "T2S":
            query["mode_used"] = {"$regex": "text|t2s|audio", "$options": "i"}
        else:
            query["mode_used"] = mode
    if email:
        query["email"] = {"$regex": email.strip(), "$options": "i"}

    total = await db.conversations.count_documents(query)
    cursor = db.conversations.find(query).sort("timestamp", -1).skip((page - 1) * limit).limit(limit)

    convs = []
    async for c in cursor:
        ts = c.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, datetime.datetime) else str(ts or "")
        convs.append({
            "id": str(c["_id"]),
            "unique_id": c.get("unique_id", "THS-USER"),
            "email": c.get("email", "Unknown"),
            "mode_used": c.get("mode_used", "General"),
            "transcript": c.get("transcript", ""),
            "timestamp": ts_str
        })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "conversations": convs
    }

@app.delete("/api/admin/conversations/{conv_id}")
async def delete_conversation_by_admin(conv_id: str):
    """Delete a single conversation log."""
    if not ObjectId.is_valid(conv_id):
        raise HTTPException(status_code=400, detail="Invalid log ID")

    res = await db.conversations.delete_one({"_id": ObjectId(conv_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation log not found")

    await log_audit_event("Delete Log", f"Admin deleted conversation log: {conv_id}")
    return {"message": "Conversation log deleted successfully"}

@app.post("/api/admin/conversations/bulk-delete")
async def bulk_delete_conversations(req: BulkDeleteRequest):
    """Bulk delete conversations by IDs or clear all."""
    if req.clear_all:
        count = await db.conversations.count_documents({})
        await db.conversations.delete_many({})
        await log_audit_event("Bulk Purge Logs", f"Admin purged all {count} conversation records.")
        return {"message": f"Purged all {count} conversation records."}

    if req.ids:
        valid_ids = [ObjectId(x) for x in req.ids if ObjectId.is_valid(x)]
        res = await db.conversations.delete_many({"_id": {"$in": valid_ids}})
        await log_audit_event("Bulk Delete Logs", f"Admin deleted {res.deleted_count} conversation logs.")
        return {"message": f"Deleted {res.deleted_count} logs."}

    return {"message": "No actions taken."}

# ==========================================
# 9. VOCABULARY & GESTURE DICTIONARY APIS
# ==========================================

@app.get("/api/admin/vocabulary")
async def list_vocabulary(category: Optional[str] = None, search: Optional[str] = None):
    """Retrieve gesture vocabulary dictionary."""
    query: Dict[str, Any] = {}
    if category and category != "all":
        query["category"] = category
    if search:
        query["$or"] = [
            {"word": {"$regex": search.strip(), "$options": "i"}},
            {"hand_posture": {"$regex": search.strip(), "$options": "i"}},
            {"category": {"$regex": search.strip(), "$options": "i"}}
        ]

    cursor = db.vocabulary.find(query).sort("word", 1)
    items = []
    async for v in cursor:
        items.append({
            "id": str(v["_id"]),
            "word": v.get("word", ""),
            "category": v.get("category", "General"),
            "description": v.get("description", ""),
            "hand_posture": v.get("hand_posture", ""),
            "difficulty": v.get("difficulty", "Beginner"),
            "video_sequences": v.get("video_sequences", 30),
            "status": v.get("status", "active")
        })
    return {"total": len(items), "vocabulary": items}

@app.post("/api/admin/vocabulary")
async def add_vocabulary_item(item: VocabItem):
    """Add a new gesture word to the dictionary."""
    existing = await db.vocabulary.find_one({"word": {"$regex": f"^{item.word.strip()}$", "$options": "i"}})
    if existing:
        raise HTTPException(status_code=400, detail="Gesture word already exists.")

    doc = {
        "word": item.word.strip(),
        "category": item.category.strip(),
        "description": item.description,
        "hand_posture": item.hand_posture,
        "difficulty": item.difficulty,
        "video_sequences": item.video_sequences or 30,
        "status": item.status or "active",
        "created_at": datetime.datetime.now(datetime.timezone.utc)
    }
    res = await db.vocabulary.insert_one(doc)
    await log_audit_event("Add Gesture", f"Added vocabulary gesture: {item.word} ({item.category})")
    return {"message": "Gesture added successfully", "id": str(res.inserted_id)}

@app.put("/api/admin/vocabulary/{id}")
async def update_vocabulary_item(id: str, item: VocabItem):
    """Update gesture vocabulary details."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")

    updates = {
        "word": item.word.strip(),
        "category": item.category.strip(),
        "description": item.description,
        "hand_posture": item.hand_posture,
        "difficulty": item.difficulty,
        "video_sequences": item.video_sequences,
        "status": item.status
    }
    res = await db.vocabulary.update_one({"_id": ObjectId(id)}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Gesture not found")

    await log_audit_event("Update Gesture", f"Updated gesture: {item.word}")
    return {"message": "Gesture updated successfully"}

@app.delete("/api/admin/vocabulary/{id}")
async def delete_vocabulary_item(id: str):
    """Delete gesture from dictionary."""
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID")

    target = await db.vocabulary.find_one({"_id": ObjectId(id)})
    if not target:
        raise HTTPException(status_code=404, detail="Gesture not found")

    await db.vocabulary.delete_one({"_id": ObjectId(id)})
    await log_audit_event("Delete Gesture", f"Deleted gesture: {target.get('word')}")
    return {"message": "Gesture deleted successfully"}


# ==========================================
# 10. SYSTEM HEALTH & AUDIT LOG APIS
# ==========================================

@app.get("/api/admin/system/health")
async def system_health():
    """Live system diagnostics, MongoDB metrics, and server runtime."""
    t0 = time.time()
    try:
        await db.command("ping")
        db_status = "Connected"
        ping_ms = round((time.time() - t0) * 1000, 2)
    except Exception as e:
        db_status = f"Error: {str(e)}"
        ping_ms = -1

    collections = await db.list_collection_names()
    user_count = await db.users.count_documents({})
    conv_count = await db.conversations.count_documents({})
    vocab_count = await db.vocabulary.count_documents({})
    audit_count = await db.audit_logs.count_documents({})

    uptime_sec = int((datetime.datetime.now(datetime.timezone.utc) - SERVER_START_TIME).total_seconds())

    return {
        "server_status": "Healthy",
        "uptime_seconds": uptime_sec,
        "database": {
            "status": db_status,
            "latency_ms": ping_ms,
            "database_name": "sih_database",
            "collections_count": len(collections),
            "counts": {
                "users": user_count,
                "conversations": conv_count,
                "vocabulary": vocab_count,
                "audit_logs": audit_count
            }
        },
        "environment": {
            "python_version": platform.python_version(),
            "os": f"{platform.system()} {platform.release()}",
            "server_start_time": SERVER_START_TIME.strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    }

@app.get("/api/admin/system/audit-logs")
async def get_audit_logs(limit: int = 50):
    """Retrieve recent administrative actions."""
    cursor = db.audit_logs.find({}).sort("timestamp", -1).limit(limit)
    logs = []
    async for item in cursor:
        ts = item.get("timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, datetime.datetime) else str(ts or "")
        logs.append({
            "id": str(item["_id"]),
            "action": item.get("action", ""),
            "details": item.get("details", ""),
            "performed_by": item.get("performed_by", "System"),
            "timestamp": ts_str
        })
    return {"logs": logs}

@app.post("/api/admin/system/audit-logs")
async def create_audit_log(entry: AuditLogItem):
    """Manually add an audit trail entry."""
    await log_audit_event(entry.action, entry.details, performed_by=entry.performed_by or "Admin")
    return {"message": "Audit log saved"}