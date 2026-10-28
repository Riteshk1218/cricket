# Building the iOS app (source only, NOT tested)

The Flutter project in `mobile/` includes the `ios/` folder, so the same app can be built
for iPhone. **It has not been built or run on iOS.** Building needs a Mac with Xcode, and
this project was developed on Linux with no Mac available. Treat the steps below as a guide
that has not been checked.

## What is already configured

* `ios/Runner/Info.plist`:
  * Display name **CricLive**.
  * `NSAppTransportSecurity` with `NSAllowsLocalNetworking` and `NSAllowsArbitraryLoads`, so the
    app can talk to `http://<laptop-ip>:8000` on your Wi-Fi. Local development only: remove
    `NSAllowsArbitraryLoads` if you ever deploy behind HTTPS.
  * `NSLocalNetworkUsageDescription`, which iOS shows when the app first contacts the laptop.
* All packages used (`http`, `web_socket_channel`, `shared_preferences`, `provider`, `uuid`,
  `intl`, `audioplayers`) support iOS.

## Steps (on a Mac)

1. Install Xcode from the Mac App Store, open it once and accept the licence.
2. Install the Flutter SDK for macOS and CocoaPods (`sudo gem install cocoapods` or `brew install cocoapods`).
3. `cd mobile && flutter pub get && cd ios && pod install && cd ..`
4. Run on the iOS Simulator: `open -a Simulator`, then `flutter run`.
   In the app, set **More → Settings → Server address** to `http://<laptop-ip>:8000`
   (the simulator can also use `http://127.0.0.1:8000` if the backend runs on the same Mac).
5. Run on your own iPhone for free:
   * Open `ios/Runner.xcworkspace` in Xcode.
   * Runner target → **Signing & Capabilities** → tick *Automatically manage signing*.
   * Team: add your Apple ID (free "Personal Team").
   * Change the Bundle Identifier to something unique, e.g. `com.yourname.criclive`.
   * Connect the iPhone, select it in Xcode, and press Run. On the phone, trust the developer
     in Settings → General → VPN & Device Management.
   * Free signing certificates expire after 7 days; rebuild to renew.

No App Store or TestFlight publishing is included, because those need a paid Apple Developer account.
