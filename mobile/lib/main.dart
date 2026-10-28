import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/api_client.dart';
import 'core/app_state.dart';
import 'core/sound.dart';
import 'core/theme.dart';
import 'screens/splash_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  runApp(CricLiveApp(state: AppState(prefs)));
}

class CricLiveApp extends StatelessWidget {
  const CricLiveApp({super.key, required this.state});
  final AppState state;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: state),
        Provider(create: (_) => ApiClient(state)),
        Provider(create: (_) => SoundPlayer(state), dispose: (_, s) => s.dispose()),
      ],
      child: Consumer<AppState>(
        builder: (context, s, _) => MaterialApp(
          title: 'CricLive',
          debugShowCheckedModeBanner: false,
          theme: buildTheme(Brightness.light),
          darkTheme: buildTheme(Brightness.dark),
          themeMode: s.themeMode,
          home: const SplashScreen(),
        ),
      ),
    );
  }
}
