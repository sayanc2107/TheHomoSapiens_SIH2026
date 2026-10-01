# TheHomoSapiens
------------------------------------------------------------------------------------------------------
> **Real-Time Indian Sign Language (ISL) Recognition & Two-Way Assistive Communication Platform**  
> *Developed by Sayan Chakraborty@Team Homosapiens for SIH2026*
------------------------------------------------------------------------------------------------------
## 📌 Project Overview

**TheHomoSapiens** is an assistive AI-powered platform developed for **Smart India Hackathon (SIH) 2026**. It bridges the communication barrier between the deaf/hard-of-hearing community and the hearing world by providing real-time, bidirectional Indian Sign Language (ISL) translation.

The system translates **ISL gestures to text/speech (Sign-to-Text/Voice)** and converts **spoken/typed words into animated sign gestures (Text-to-Sign)**. It features an advanced **Anchor-Point Perception Engine** that eliminates visual line clutter, focusing on critical anatomical keypoints (wrist root origin, palm centroid, and fingertip actuators) for robust, high-accuracy recognition.
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
## 🚀 How It Works

1. **Vision & Anchor-Point Perception**:
   - Captures live video stream from a web camera using MediaPipe Tasks HandLandmarker (`hand_landmarker.task`).
   - Replaces traditional noisy skeleton lines with **Anatomical Anchor Points**:
     - **Root Anchor (Wrist #0)**: Spatial reference origin for coordinate normalization across varying distances.
     - **Palm Centroid Anchor**: Geometric center of mass calculated from knuckle polygon (MCPs) to establish palm normal and facing direction.
     - **Fingertip Anchors (#4, #8, #12, #16, #20)**: High-visibility actuators tracking flexion, pointing angles, and multi-finger pinches.
   - Tracks both hands simultaneously for complex dual-hand gestures.

2. **Hybrid Recognition Pipeline**:
   - **Real-Time Client-Side ISL Engine**: Evaluates 3D landmark geometry and temporal velocity vectors in browser JavaScript with zero latency.
   - **Machine Learning Classifier**: Powered by a temporal-pooling Multi-Layer Perceptron (MLP) trained on sequence statistics (mean, variance, and kinematic displacement deltas) over 30-frame temporal windows.
   - **Dual-Hand & Single-Hand ISL Vocabulary**: Recognizes core ISL phrases (*Namaste*, *Help*, *Book*, *Love*, *Home*, *Welcome*, *Thank You*, *Water*, *Eat*, *Drink*, *Father*, *Mother*, etc.) with automatic fallback to fingerspelled alphabet characters (A–Z).

3. **Two-Way Communication**:
   - **Sign-to-Speech**: Detected gestures are translated to text and spoken aloud via speech synthesis (Web Speech API in browser, `pyttsx3` in desktop app).
   - **Text-to-Sign**: Spoken or written phrases are processed and rendered through interactive 3D/2D visual sign avatars.

4. **Role-Based Access & Admin Control**:
   - Secure authentication featuring User and SuperAdmin roles.
   - Dynamic vocabulary manager, real-time analytics dashboard, translation audit logging, and direct access controls.
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
## 🛠️ Tech Stacks Used

### **Computer Vision & Machine Learning**
- **MediaPipe Tasks 1.0+** (`HandLandmarker`, `VisionRunningMode.VIDEO`) – High-speed 21-point 3D landmark perception.
- **OpenCV (`cv2`)** – Frame capture, real-time matrix transformations, and visual HUD rendering.
- **Scikit-Learn (`sklearn`)** – Multi-Layer Perceptron (`MLPClassifier`) for temporal sequence gesture classification.
- **NumPy** – Vectorized coordinate manipulation, spatial geometry, and tensor processing.
- **Joblib** – Model serialization and artifact persistence.

### **Backend & APIs**
- **Python 3.10+** – Core server environment.
- **FastAPI** – High-performance asynchronous REST API framework.
- **Uvicorn** – ASGI web server with auto-reload capabilities.
- **Motor / PyMongo** – Asynchronous MongoDB driver for real-time translation logs, vocabulary actions, and user profiles.
- **OAuth2 / JWT & Passlib (Bcrypt)** – Secure token-based authentication and salted password hashing.

### **Frontend & Interface**
- **HTML5 & Vanilla CSS** – Semantic layout, custom UI styling, and responsive design.
- **Tailwind CSS** – Modern responsive utilities, sleek dark/light theme switching.
- **JavaScript (ES6+)** – Client-side MediaPipe integration, vector math, and asynchronous event loops.
- **HTML5 Canvas API** – High-framerate anchor-point rendering and avatar animation.
- **Font Awesome 6** – Accessible iconography and visual indicators.

### **Audio & Accessibility**
- **Web Speech API (`SpeechSynthesis`)** – In-browser voice synthesis.
- **Pyttsx3** – Offline text-to-speech engine for desktop applications.

---

## 📂 Project Architecture

```text
TheHomoSapiens_SIH2026/
├── android_app/            # Standalone Native Android Mobile App (Gradle/Java)
├── index.html              # Main user portal & live camera ISL recognition
├── login.html              # Secure member authentication interface
├── register.html           # New user registration portal
├── admin.html              # SuperAdmin dashboard, analytics & vocabulary management
├── main_app.py             # FastAPI backend (Auth, ISL Predict, Vocabulary, Logging)
├── anchor_hand_test.py     # Standalone OpenCV anchor-point perception test
├── isl_realtime.py         # Real-time desktop ISL runner with TTS audio speech
├── collect_data.py         # Dataset recorder (30 frames x 30 sequences per action)
├── train_isl_model.py      # Feature engineering and MLP classifier training script
├── hand_landmarker.task    # MediaPipe HandLandmarker pre-trained vision weights
├── models/                 # Serialized model weights & class dictionaries
└── requirements.txt        # Python backend & ML dependencies
```

---

## 📱 Standalone Mobile App (Android APK)
The project now includes a **Native Android Application** located in the `android_app/` directory:
- **Zero-Friction Camera Access**: Bypasses browser restrictions by natively granting camera and audio capture via hardware acceleration.
- **Native Android Bridge**: Integrates native Android Text-to-Speech (TTS), haptic vibrations, and toast alerts.
- **Easy Compilation**: Open `android_app/` in Android Studio or push to GitHub to trigger the automated `.github/workflows/build_apk.yml` workflow for a downloadable `.apk` file!

---

## ⚡ Quick Start Guide

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Start the Backend & Web Application
```powershell
python -m uvicorn main_app:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser and navigate to:
```
http://127.0.0.1:8000/index.html
```

### 3. Run Standalone Anchor Point Tracker
```powershell
python anchor_hand_test.py
```

### 4. Run Desktop Real-Time Recognition (with Audio)
```powershell
python isl_realtime.py
```

---

## 👨‍💻 Developer & Team Credits

**Developed by Sayan Chakraborty@Team Homosapiens for SIH2026**
