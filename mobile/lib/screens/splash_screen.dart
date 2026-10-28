import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import 'home_shell.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _go();
  }

  Future<void> _go() async {
    final api = context.read<ApiClient>();
    // Check the server, but continue either way: Home shows a clear error with the address to fix.
    await Future.wait([api.ping(), Future.delayed(const Duration(milliseconds: 900))]);
    if (!mounted) return;
    Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const HomeShell()));
  }

  @override
  Widget build(BuildContext context) => const Scaffold(
        backgroundColor: pitch,
        body: Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.sports_cricket, size: 88, color: Colors.white),
            SizedBox(height: 16),
            Text('CricLive', style: TextStyle(color: Colors.white, fontSize: 34, fontWeight: FontWeight.w900)),
            SizedBox(height: 4),
            Text('Live cricket scores', style: TextStyle(color: Colors.white70)),
            SizedBox(height: 32),
            SizedBox(width: 28, height: 28, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3)),
          ]),
        ),
      );
}
