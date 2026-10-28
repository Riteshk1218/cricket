import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/i18n.dart';

/// Login and registration. New accounts are always viewers; admins promote scorers on the website.
class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool _register = false;
  bool _busy = false;
  String? _error;
  final _user = TextEditingController();
  final _pass = TextEditingController();
  final _email = TextEditingController();
  final _name = TextEditingController();

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final api = context.read<ApiClient>();
    try {
      if (_register) {
        await api.register(_user.text.trim(), _email.text.trim(), _pass.text, _name.text.trim());
      } else {
        await api.login(_user.text.trim(), _pass.text);
      }
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(context.t(_register ? 'register' : 'login'))),
      body: ListView(padding: const EdgeInsets.all(20), children: [
        const Icon(Icons.sports_cricket, size: 64),
        const SizedBox(height: 16),
        if (_error != null)
          Container(
            padding: const EdgeInsets.all(10),
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(color: Theme.of(context).colorScheme.errorContainer, borderRadius: BorderRadius.circular(8)),
            child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.onErrorContainer)),
          ),
        TextField(controller: _user, decoration: InputDecoration(labelText: context.t('username')), autocorrect: false, textInputAction: TextInputAction.next),
        const SizedBox(height: 12),
        if (_register) ...[
          TextField(controller: _name, decoration: InputDecoration(labelText: context.t('name')), textInputAction: TextInputAction.next),
          const SizedBox(height: 12),
          TextField(controller: _email, decoration: InputDecoration(labelText: context.t('email')), keyboardType: TextInputType.emailAddress, textInputAction: TextInputAction.next),
          const SizedBox(height: 12),
        ],
        TextField(controller: _pass, decoration: InputDecoration(labelText: context.t('password')), obscureText: true, onSubmitted: (_) => _submit()),
        const SizedBox(height: 20),
        FilledButton(onPressed: _busy ? null : _submit, child: Padding(padding: const EdgeInsets.all(12), child: Text(context.t(_register ? 'register' : 'login')))),
        TextButton(
          onPressed: () => setState(() => _register = !_register),
          child: Text(_register ? 'Already have an account? ${context.t('login')}' : 'New here? ${context.t('register')}'),
        ),
      ]),
    );
  }
}
