# Fraud Detection Mobile Application (Android)

Professional Flutter Android mobile client for the ML-powered Fraud Detection platform.

## Design System & Theme
- **UI Framework**: Flutter with **Material 3** enabled (`useMaterial3: true`).
- **Color Palette**:
  - Deep Graphite / Charcoal backgrounds (`#0D0F12`, `#16191F`, `#1E232B`)
  - Emerald & Teal cybersecurity accents (`#00E599`, `#00D2B4`, `#00B4D8`)
  - Elevated contrast text (`#F1F5F9`, `#94A3B8`)
- **Structure**:
  - `lib/main.dart`: Application entry point with dark system UI overlay configuration.
  - `lib/theme/app_theme.dart`: Centralized Material 3 ThemeData definition.
  - `lib/screens/landing_screen.dart`: Starting dashboard screen presenting system readiness.
  - `lib/widgets/app_brand_header.dart`: Brand header with cybersecurity badges.
  - `lib/widgets/system_status_card.dart`: Architecture readiness status.

## Current Stage Status
- Standalone starting screen created.
- Backend pipeline is in standby (unconnected).
- No mock/fake fraud predictions or mock transaction data have been added.
- Existing Flask web application and ML models in the root folder remain untouched.

## Prerequisites to Run on Windows
1. **Flutter SDK**:
   - Download from: https://docs.flutter.dev/get-started/install/windows
   - Extract to `C:\src\flutter` (or a location of your choice).
   - Add `C:\src\flutter\bin` to your system environment `PATH`.
2. **Android SDK / Android Studio**:
   - Download Android Studio from: https://developer.android.com/studio
   - Install the Android SDK, Android SDK Command-line Tools, and Android SDK Build-Tools via Android Studio SDK Manager.
   - Set `ANDROID_HOME` to `C:\Users\<YourUser>\AppData\Local\Android\Sdk`.
3. **Verify Tooling**:
   ```powershell
   flutter doctor
   ```

## Running the App
Once Flutter and Android SDK are installed:
```powershell
cd mobile_app
flutter pub get
flutter format .
flutter analyze
flutter run
```
