import 'package:flutter/material.dart';

const pitch = Color(0xFF1F8A70);
const ballRed = Color(0xFFDC2626);
const gold = Color(0xFFF2B01E);

ThemeData buildTheme(Brightness b) {
  final scheme = ColorScheme.fromSeed(seedColor: pitch, brightness: b);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    cardTheme: const CardThemeData(margin: EdgeInsets.zero, clipBehavior: Clip.antiAlias),
    inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder()),
    appBarTheme: AppBarTheme(backgroundColor: b == Brightness.light ? pitch : null, foregroundColor: b == Brightness.light ? Colors.white : null),
  );
}

Color hexColor(String? hex, [Color fallback = pitch]) {
  if (hex == null || !RegExp(r'^#?[0-9a-fA-F]{6}$').hasMatch(hex)) return fallback;
  return Color(int.parse('FF${hex.replaceFirst('#', '')}', radix: 16));
}
