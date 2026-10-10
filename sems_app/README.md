# Smart Energy Management System (SEMS) - Flutter Mobile App 📱⚡☀️

A complete, production-ready cross-platform **Flutter + Dart** mobile app designed for **both younger and senior / elder generations** to monitor household solar, battery storage, and utility grid power, calculate real-time **units used today (kWh)**, estimate the **1-day total electricity bill (in ₹)** using official **TNEB domestic tariff slabs**, and deliver **hourly push notifications**.

---

## 🌟 Key Features & Upgradations

### 1. 👴👵 Elder / Senior Friendly Mode
- **High-Contrast, Large Text (1.35x scale)**: Extra-large numbers and buttons designed for seniors.
- **Simplified Terminology**: Plain, clear phrases in both **Tamil (தமிழ்)** and **English** (e.g. *"இன்றைய மின்சார பயன்பாடு"* instead of *"Aggregated Telemetry Load"*).
- **🔊 Voice Readout (Text-To-Speech)**: Tap the speaker button anytime to hear:
  > *"வணக்கம். இன்று நீங்கள் பயன்படுத்திய மின்சாரம் 14.2 யூனிட்டுகள், கட்டணம் 28 ரூபாய்..."*
- **One-Touch Age Switcher**: Instantly toggle between **Young / Modern View** and **Senior / Elder View** in Onboarding or Settings.

### 2. ⚡ Units Used & 1-Day Total Amount (TNEB Slabs)
- Tracks **Units Used Today (kWh)** in real-time.
- Calculates **Total Amount for 1 Day (₹)** using current official Tamil Nadu Electricity Board (TNEB / TANGEDCO LT-IA) domestic slabs:
  - **0 - 100 Units**: FREE (₹0.00 Government Subsidy)
  - **101 - 400 Units**: ₹4.70 / Unit
  - **401 - 500 Units**: ₹6.30 / Unit
  - **501 - 600 Units**: ₹8.40 / Unit
  - **601 - 800 Units**: ₹9.45 / Unit
  - **801 - 1,000 Units**: ₹10.50 / Unit
  - **1,000+ Units**: ₹11.55 / Unit
- Displays **Rupees Saved Today** via solar and battery storage!
- **TNEB Comparison Screen**: Side-by-side view of normal EB bill vs SEMS AI bill.

### 3. ⏰ Hourly Push Notifications
- Periodic hourly alerts firing every hour at `:00`:
  > *"⚡ Hourly Energy Summary: Units used this hour: 1.85 kWh | Today total: 14.20 Units (Cost: ₹28.50)"*
- **Test Notification Button**: Available in the Alerts Hub screen to instantly preview notifications.
- Ready for local background notifications and Firebase Cloud Messaging (FCM).

### 4. 🔌 Appliance-Wise Unit & Cost Breakdown
- Interactive runtime sliders for:
  - ❄️ Air Conditioner (1.5 Ton)
  - 🧊 Refrigerator (Double Door)
  - 🚿 Water Heater / Geyser
  - 📺 Smart Television
  - 🧺 Washing Machine
  - 💨 Ceiling Fans & Lights
- Displays individual units consumed and cost for each appliance.

### 5. 📤 PDF Receipt & WhatsApp / SMS Share
- **One-Click Share**: Send daily electricity reports to family on WhatsApp or SMS.
- **Download / Print PDF**: Generates a standard A4 daily receipt.

---

## 🏗️ Architecture & Screens

```
sems_app/
├── lib/
│   ├── main.dart                      # App entry, MultiProvider & Theme
│   ├── core/
│   │   ├── constants.dart             # Backend API URLs & TNEB Slabs
│   │   ├── localization.dart          # Bilingual dictionary (English & தமிழ்)
│   │   ├── theme.dart                 # High-contrast Elder & Modern Dark/Light themes
│   │   └── notification_service.dart  # Hourly push notification scheduler
│   ├── models/
│   │   ├── dashboard_model.dart       # FastAPI JSON parser with offline fallback
│   │   ├── energy_usage_model.dart    # TNEB slab calculator & 24h simulation
│   │   └── alert_model.dart           # Hourly alert model
│   ├── services/
│   │   ├── api_service.dart           # FastAPI HTTP client
│   │   ├── tts_service.dart           # Voice text-to-speech engine
│   │   └── usage_calculator.dart      # Appliance unit math
│   ├── providers/
│   │   ├── user_profile_provider.dart # Age mode, language & preferences
│   │   └── energy_provider.dart       # Live state management & 30s polling
│   ├── widgets/
│   │   ├── energy_card.dart           # Live Solar, Battery, Grid, Load cards
│   │   ├── cost_banner.dart           # 1-day cost, unit count & voice TTS
│   │   ├── usage_gauge.dart           # Circular unit progress & slab badge
│   │   └── hourly_bar_chart.dart      # 24-hour fl_chart bar graph
│   └── screens/
│       ├── splash_screen.dart         # Intro logo and navigation router
│       ├── onboarding_screen.dart     # Age profile & language selector
│       ├── home_screen.dart           # Main dashboard & live telemetry
│       ├── usage_screen.dart          # Detailed unit tracking & 1-day bill
│       ├── appliance_screen.dart      # Appliance sliders & consumption
│       ├── battery_screen.dart        # BESS SOC % & 10-hour backup check
│       ├── alerts_screen.dart         # Hourly notification history & test trigger
│       ├── tneb_compare_screen.dart   # Standard EB vs SEMS Solar AI savings
│       ├── export_screen.dart         # WhatsApp share & PDF print
│       └── settings_screen.dart       # Change age mode, language & server IP
```

---

## 🚀 How to Run

### Step 1: Start the FastAPI Backend
From the root workspace directory (`d:\Smart Energy Management System`):
```powershell
uvicorn server:app --reload --port 8080
```

### Step 2: Set Up Flutter (If Not Yet Installed)
1. Download Flutter SDK from [flutter.dev](https://docs.flutter.dev/get-started/install/windows/mobile).
2. Extract to `C:\flutter` and add `C:\flutter\bin` to your Windows `PATH` environment variable.
3. Verify in PowerShell:
   ```powershell
   flutter doctor
   ```

### Step 3: Run the Flutter App
Navigate into the `sems_app` folder:
```powershell
cd sems_app
flutter pub get
flutter run
```

- **On Android Emulator**: Default server URL is `http://10.0.2.2:8080`.
- **On Real Android / iPhone**: Enter your computer's local Wi-Fi IP (e.g. `http://192.168.1.15:8080`) in the app's **Settings** screen.
- **Offline / Standalone**: If the server is offline, the app automatically runs in self-contained simulation mode so all screens and features can be tested immediately!
