import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/app_state.dart';
import '../core/i18n.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});
  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late final TextEditingController _name;
  late final TextEditingController _phone;
  String? _msg;

  @override
  void initState() {
    super.initState();
    final u = context.read<AppState>().user ?? {};
    _name = TextEditingController(text: '${u['display_name'] ?? ''}');
    _phone = TextEditingController(text: '${u['phone'] ?? ''}');
    // Refresh the cached profile (role may have changed on the website).
    context.read<ApiClient>().get('/auth/me/').then((u) {
      if (!mounted) return;
      final s = context.read<AppState>();
      s.setSession(access: s.accessToken, userData: u as Map<String, dynamic>);
    }).catchError((_) {});
  }

  Future<void> _save() async {
    final api = context.read<ApiClient>();
    final s = context.read<AppState>();
    try {
      final u = await api.patch('/auth/me/', {'display_name': _name.text.trim(), 'phone': _phone.text.trim(), 'preferred_language': s.language});
      await s.setSession(access: s.accessToken, userData: u as Map<String, dynamic>);
      setState(() => _msg = 'Saved');
    } catch (e) {
      setState(() => _msg = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    final u = s.user ?? {};
    return Scaffold(
      appBar: AppBar(title: Text(context.t('profile'))),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        CircleAvatar(radius: 36, child: Text('${u['username'] ?? '?'}'.substring(0, 1).toUpperCase(), style: const TextStyle(fontSize: 28))),
        const SizedBox(height: 8),
        Text('${u['username'] ?? ''}', textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
        Text('${u['email'] ?? ''} · ${s.role.replaceAll('_', ' ')}', textAlign: TextAlign.center),
        const SizedBox(height: 20),
        TextField(controller: _name, decoration: InputDecoration(labelText: context.t('name'))),
        const SizedBox(height: 12),
        TextField(controller: _phone, decoration: const InputDecoration(labelText: 'Phone'), keyboardType: TextInputType.phone),
        const SizedBox(height: 16),
        FilledButton(onPressed: _save, child: Text(context.t('save'))),
        if (_msg != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_msg!, textAlign: TextAlign.center)),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          icon: const Icon(Icons.logout),
          label: Text(context.t('logout')),
          onPressed: () async {
            await context.read<ApiClient>().logout();
            if (context.mounted) Navigator.of(context).pop();
          },
        ),
      ]),
    );
  }
}
