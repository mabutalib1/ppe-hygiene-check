# Mobile app (Expo, React Native)

The supervisor's view: live video with boxes, a status card per person, and an alert feed that buzzes when someone breaks a rule. It only displays what the backend sends and does no detection itself.

| Screen | Shows |
|---|---|
| Connect | Server address + "Test connection" (calls `/health`), saved after the first success. Tap the address in the top bar to change it |
| Live | Annotated video (`/stream` in a WebView) + one card per person: mask, hairnet, gloves, uniform in green / red / grey |
| Alerts | Newest first: snapshot, person, item, removed/missing, time, ongoing or how long it lasted. Tap for the full snapshot. Pull to refresh |

Built on Expo SDK 58. Dependencies: `react-native-webview` (MJPEG), `expo-notifications` (local alerts), `@react-native-async-storage/async-storage` (saved server address).

## Run

```bash
cd mobile
npm install
npx expo start
```

Scan the QR code with **Expo Go** on your phone. The phone, the laptop running Expo and the backend laptop must be on the same Wi-Fi (use a phone hotspot if the venue Wi-Fi isolates devices).

In the app, enter the backend address, e.g. `192.168.1.20:8000`. To find the laptop's IP: `ipconfig getifaddr en0` (Mac) or `ipconfig` (Windows).

No model yet? Run the backend with `DETECTOR=fake CAMERA_SOURCE=synthetic` and the app shows two people and a scripted gloves/mask violation every minute.

## How it talks to the backend

- **Video:** WebView showing `/stream`. React Native's `Image` doesn't reliably play MJPEG
- **Status + alerts:** one WebSocket to `/ws`. Status messages update the cards; `violation` events go into Alerts and fire a local notification; `resolved` events close them with a duration
- **Reconnect:** retries every 2 s with a "Reconnecting…" banner
- **History:** Alerts loads `/events` when opened and after every reconnect

## Limits (say this if asked)

- Local notifications work while the app is open or in the background. True push when the app is fully closed needs a push service and a published build. That's out of scope
- The backend uses plain `http://` on the local network. Expo Go allows that; a standalone build would need cleartext traffic enabled on Android
