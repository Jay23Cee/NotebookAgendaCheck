# Android Launcher APK (Phase 1)

This Android app is a local launcher for the Notebook Agenda Check NiceGUI service.

It does not embed Python. It expects the backend to be running at:

- `http://127.0.0.1:8080`
- health probe: `http://127.0.0.1:8080/_nach/health`

## Features

- Startup health probe for local backend readiness
- WebView launch when backend is healthy
- Offline state with:
  - `Retry`
  - `Open Termux`
- Loopback-only cleartext policy via `network_security_config.xml`

## Prerequisites

- JDK 17
- Android SDK / Android Studio
- `JAVA_HOME` set
- `ANDROID_SDK_ROOT` (or `ANDROID_HOME`) set

## Build Debug APK

From `android/launcher/`:

```powershell
.\gradlew.bat :app:assembleDebug
```

Output:

- `app/build/outputs/apk/debug/app-debug.apk`

## Build Release APK

1. Generate a keystore:

```powershell
keytool -genkeypair -v -keystore release-upload.jks -alias notebookagenda -keyalg RSA -keysize 2048 -validity 10000
```

2. Create `android/launcher/keystore.properties` (do not commit):

```text
storeFile=release-upload.jks
storePassword=YOUR_STORE_PASSWORD
keyAlias=notebookagenda
keyPassword=YOUR_KEY_PASSWORD
```

3. Build release:

```powershell
.\gradlew.bat :app:assembleRelease
```

Output:

- `app/build/outputs/apk/release/app-release.apk`

## Install APK with ADB

```powershell
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

## Runtime Check

1. Start backend on device:

```bash
scripts/android/start_na_app.sh
```

2. Open launcher app:
- Healthy backend -> dashboard opens in WebView
- Unhealthy backend -> offline state; use `Retry` after starting service
