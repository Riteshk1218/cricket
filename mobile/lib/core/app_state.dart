import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// App-wide settings and session, persisted on the device.
class AppState extends ChangeNotifier {
  AppState(this._prefs) {
    var saved = _prefs.getString('serverUrl');
    // Once, after updating to the hosted-server build: switch an old laptop/emulator
    // (http://) address to the hosted server. Users can change it back in Settings.
    if (_prefs.getBool('hostedServerMigrated') != true) {
      if (saved != null && saved.startsWith('http://')) saved = null;
      _prefs.setBool('hostedServerMigrated', true);
    }
    _serverUrl = saved ?? defaultServerUrl;
    _language = _prefs.getString('language') ?? 'en';
    _themeMode = ThemeMode.values[_prefs.getInt('themeMode') ?? ThemeMode.system.index];
    _sound = _prefs.getBool('sound') ?? true;
    _volume = _prefs.getDouble('volume') ?? 0.7;
    _animations = _prefs.getBool('animations') ?? true;
    _access = _prefs.getString('access');
    _refresh = _prefs.getString('refresh');
    final u = _prefs.getString('user');
    if (u != null) user = jsonDecode(u) as Map<String, dynamic>;
    _visitorId = _prefs.getString('visitorId') ?? _newVisitorId();
    _prefs.setString('visitorId', _visitorId);
  }

  /// The hosted server on Render. To use a laptop on the same Wi-Fi instead, enter
  /// its address in Settings (for example http://192.168.1.10:8000; the Android
  /// emulator reaches the host computer at http://10.0.2.2:8000).
  static const defaultServerUrl = 'https://criclive-ur9a.onrender.com';

  final SharedPreferences _prefs;
  late String _serverUrl;
  late String _language;
  late ThemeMode _themeMode;
  late bool _sound;
  late double _volume;
  late bool _animations;
  late String _visitorId;
  String? _access;
  String? _refresh;
  Map<String, dynamic>? user;

  String get serverUrl => _serverUrl;
  String get apiUrl => '$_serverUrl/api';
  String get wsUrl => _serverUrl.replaceFirst(RegExp(r'^http'), 'ws');
  String get language => _language;
  ThemeMode get themeMode => _themeMode;
  bool get sound => _sound;
  double get volume => _volume;
  bool get animations => _animations;
  String get visitorId => _visitorId;
  String? get accessToken => _access;
  String? get refreshToken => _refresh;
  bool get loggedIn => _access != null && user != null;
  String get role => (user?['role'] as String?) ?? 'viewer';
  bool get canScore => loggedIn && const ['scorer', 'tournament_admin', 'super_admin'].contains(role);

  static String _newVisitorId() {
    final r = Random.secure();
    return List.generate(16, (_) => r.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
  }

  Future<void> setServerUrl(String url) async {
    var u = url.trim();
    if (!u.startsWith('http')) {
      // A laptop IP or localhost uses plain http; a hosted address such as
      // criclive.onrender.com uses https.
      final local = RegExp(r'^(localhost|\d+\.\d+\.\d+\.\d+)(:|/|$)').hasMatch(u);
      u = '${local ? 'http' : 'https'}://$u';
    }
    u = u.replaceAll(RegExp(r'/+$'), '');
    // Only the laptop server needs the :8000 port; https sites use the default port.
    if (u.startsWith('http://') && !RegExp(r':\d+$').hasMatch(u)) u = '$u:8000';
    _serverUrl = u;
    await _prefs.setString('serverUrl', u);
    notifyListeners();
  }

  Future<void> setLanguage(String v) async {
    _language = v;
    await _prefs.setString('language', v);
    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode m) async {
    _themeMode = m;
    await _prefs.setInt('themeMode', m.index);
    notifyListeners();
  }

  Future<void> setSound(bool v) async {
    _sound = v;
    await _prefs.setBool('sound', v);
    notifyListeners();
  }

  Future<void> setVolume(double v) async {
    _volume = v;
    await _prefs.setDouble('volume', v);
    notifyListeners();
  }

  Future<void> setAnimations(bool v) async {
    _animations = v;
    await _prefs.setBool('animations', v);
    notifyListeners();
  }

  Future<void> setSession({String? access, String? refresh, Map<String, dynamic>? userData}) async {
    _access = access;
    if (refresh != null) _refresh = refresh;
    if (userData != null) user = userData;
    if (access == null) {
      _refresh = null;
      user = null;
      await _prefs.remove('access');
      await _prefs.remove('refresh');
      await _prefs.remove('user');
    } else {
      await _prefs.setString('access', access);
      if (_refresh != null) await _prefs.setString('refresh', _refresh!);
      if (user != null) await _prefs.setString('user', jsonEncode(user));
    }
    notifyListeners();
  }
}
