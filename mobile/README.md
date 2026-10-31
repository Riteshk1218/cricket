# CricLive mobile app (Flutter)

Android (debug APK) and iOS (source only) app for the cricket live scoring system.

```powershell
flutter pub get
flutter run                  # uses the hosted Render server by default; change it in Settings
flutter build apk --debug    # build\app\outputs\flutter-apk\app-debug.apk
flutter analyze; flutter test
```

On a real phone, open **More → Settings → Server address**, enter `http://<laptop-wifi-ip>:8000`
and tap **Save & Test connection**. See `../docs/WINDOWS_SETUP.md` (Steps 13–16) and `../docs/IOS_BUILD.md`.

Code layout: `lib/core` (settings, REST client, WebSocket with reconnect, translations, sounds),
`lib/widgets` (cards, scorecard, celebration overlay), `lib/screens` (all screens including the scorer panel).
