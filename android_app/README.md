# TheHomoSapiens ISL - Standalone Android Mobile Application

This is the standalone Android native mobile application for **TheHomoSapiens SIH 2026** Indian Sign Language recognition platform.

---

## 📱 Features

1. **Hardware-Accelerated Camera Pipeline**:
   - Implements native `WebChromeClient` with automated camera permission approval (`RESOURCE_VIDEO_CAPTURE`).
   - Seamlessly captures video without browser prompt restrictions or SSL/HTTPS warnings on local networks.
2. **Native JavaScript Bridge (`WebAppInterface`)**:
   - Direct integration between JavaScript frontend and Android native features:
     - Native Android Text-to-Speech (TTS)
     - Device haptic feedback vibration
     - Native Toast notifications
3. **Dynamic Server Configuration**:
   - Pre-configured to point to your live backend (`http://192.168.0.4:8000/index.html`).
   - Easily customizable to production cloud endpoints or local tunnels.
4. **Offline Capability & Pull-to-Refresh**:
   - `SwipeRefreshLayout` support to quickly reload views.

---

## 🛠️ How to Build & Generate the APK

### Method 1: Build in Android Studio (Recommended)
1. Open **Android Studio**.
2. Click **File -> Open...** and select the `android_app` directory in this project (`e:\PROGRAMMING\TheHomoSapiens_SIH2026\android_app`).
3. Wait for Gradle sync to complete.
4. Connect your Android phone via USB (with USB Debugging enabled) and click the green **Run (▶)** button.
5. To generate a standalone `.apk` file:
   - Click **Build -> Build Bundle(s) / APK(s) -> Build APK(s)**.
   - Android Studio will output: `app/build/outputs/apk/debug/app-debug.apk`.
   - Transfer this `.apk` to any Android phone and install!

### Method 2: Automated GitHub Actions Build (Zero Setup)
1. Push this project to GitHub.
2. Go to the **Actions** tab in your repository.
3. The workflow **"Build Standalone Android APK"** will automatically compile the project and provide a download link for `TheHomoSapiens_ISL_App.apk` under **Artifacts**!

### Method 3: Command Line Build (with Gradle)
```bash
cd android_app
./gradlew assembleDebug
```
The APK will be generated at:
`android_app/app/build/outputs/apk/debug/app-debug.apk`
