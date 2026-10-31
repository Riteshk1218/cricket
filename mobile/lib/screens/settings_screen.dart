import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/app_state.dart';
import '../core/i18n.dart';
import '../core/sound.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _server = TextEditingController(text: context.read<AppState>().serverUrl);
  String? _result;
  bool _testing = false;

  Future<void> _saveServer() async {
    setState(() {
      _testing = true;
      _result = null;
    });
    final s = context.read<AppState>();
    await s.setServerUrl(_server.text);
    _server.text = s.serverUrl;
    if (!mounted) return;
    final ok = await context.read<ApiClient>().ping();
    if (mounted) {
      setState(() {
        _testing = false;
        _result = ok ? '✅ Connected to ${s.serverUrl}' : '❌ Cannot reach ${s.serverUrl}. Check the address. For a laptop server: same Wi-Fi, and Windows Firewall allows port 8000.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: Text(context.t('settings'))),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text(context.t('server'), style: const TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        TextField(
          controller: _server,
          keyboardType: TextInputType.url,
          autocorrect: false,
          decoration: const InputDecoration(hintText: 'https://criclive-ur9a.onrender.com', helperText: 'Online: https://criclive-ur9a.onrender.com · Laptop on Wi-Fi: http://<IP from "ipconfig">:8000', helperMaxLines: 2),
        ),
        const SizedBox(height: 8),
        FilledButton.icon(onPressed: _testing ? null : _saveServer, icon: const Icon(Icons.wifi_tethering), label: Text('${context.t('save')} & ${context.t('test_connection')}')),
        if (_result != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_result!)),
        const Divider(height: 32),
        Text(context.t('language'), style: const TextStyle(fontWeight: FontWeight.bold)),
        SegmentedButton<String>(
          segments: [for (final e in languages.entries) ButtonSegment(value: e.key, label: Text(e.value))],
          selected: {s.language},
          onSelectionChanged: (v) => s.setLanguage(v.first),
        ),
        const SizedBox(height: 16),
        Text(context.t('theme'), style: const TextStyle(fontWeight: FontWeight.bold)),
        SegmentedButton<ThemeMode>(
          segments: [
            ButtonSegment(value: ThemeMode.system, label: Text(context.t('system'))),
            ButtonSegment(value: ThemeMode.light, label: Text(context.t('light'))),
            ButtonSegment(value: ThemeMode.dark, label: Text(context.t('dark'))),
          ],
          selected: {s.themeMode},
          onSelectionChanged: (v) => s.setThemeMode(v.first),
        ),
        const Divider(height: 32),
        SwitchListTile(contentPadding: EdgeInsets.zero, title: Text(context.t('sound')), value: s.sound, onChanged: s.setSound),
        ListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(context.t('volume')),
          subtitle: Slider(value: s.volume, onChanged: s.sound ? s.setVolume : null, onChangeEnd: (_) => context.read<SoundPlayer>().play('four')),
        ),
        SwitchListTile(contentPadding: EdgeInsets.zero, title: Text(context.t('animations')), value: s.animations, onChanged: s.setAnimations),
      ]),
    );
  }
}
