import 'package:cricket_live/core/app_state.dart';
import 'package:cricket_live/core/i18n.dart';
import 'package:cricket_live/core/theme.dart';
import 'package:cricket_live/widgets/common.dart';
import 'package:cricket_live/widgets/match_card.dart';
import 'package:cricket_live/widgets/scorecard.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

Map<String, dynamic> team(int id, String name, String short) => {'id': id, 'name': name, 'short_name': short, 'logo': null, 'primary_color': '#0f766e'};

Future<AppState> makeState([Map<String, Object> values = const {}]) async {
  SharedPreferences.setMockInitialValues(values);
  return AppState(await SharedPreferences.getInstance());
}

Widget wrap(AppState s, Widget child) => ChangeNotifierProvider.value(value: s, child: MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child))));

void main() {
  group('AppState', () {
    test('server address is normalised for LAN use', () async {
      final s = await makeState();
      expect(s.serverUrl, 'http://10.0.2.2:8000');
      await s.setServerUrl(' 192.168.1.10 ');
      expect(s.serverUrl, 'http://192.168.1.10:8000');
      expect(s.apiUrl, 'http://192.168.1.10:8000/api');
      expect(s.wsUrl, 'ws://192.168.1.10:8000');
      await s.setServerUrl('http://192.168.1.10:9000/');
      expect(s.serverUrl, 'http://192.168.1.10:9000');
    });

    test('settings and session persist', () async {
      final s = await makeState();
      await s.setLanguage('mr');
      await s.setVolume(0.3);
      await s.setSession(access: 'a', refresh: 'r', userData: {'username': 'scorer1', 'role': 'scorer'});
      final again = AppState(await SharedPreferences.getInstance());
      expect(again.language, 'mr');
      expect(again.volume, 0.3);
      expect(again.canScore, isTrue);
      expect(again.visitorId, s.visitorId);
      await again.setSession(access: null);
      expect(again.loggedIn, isFalse);
      expect(again.canScore, isFalse);
    });
  });

  test('translations fall back to English', () {
    expect(tr('mr', 'six'), 'षटकार!');
    expect(tr('hi', 'four'), 'चौका!');
    expect(tr('xx', 'wicket'), 'WICKET!');
    expect(tr('en', 'unknown_key'), 'unknown_key');
  });

  test('team colours parse safely', () {
    expect(hexColor('#ff0000'), const Color(0xFFFF0000));
    expect(hexColor('bad'), pitch);
    expect(hexColor(null), pitch);
  });

  testWidgets('match card shows live scores and teams', (tester) async {
    final s = await makeState();
    await tester.pumpWidget(wrap(s, MatchCard({
      'id': 1, 'version': 3, 'status': 'live', 'stage': 'league', 'match_number': 1,
      'scheduled_at': '2026-10-28T10:00:00Z', 'tournament': {'id': 1, 'name': 'Pune Premier T20'},
      'team_a': team(1, 'Pune Panthers', 'PNP'), 'team_b': team(2, 'Kothrud Kings', 'KTK'),
      'scores': {'1': [{'innings': 1, 'runs': 45, 'wickets': 2, 'overs': '5.3', 'is_super_over': false}]},
      'result': null, 'batting_team_id': 1, 'target': null,
    })));
    expect(find.text('Pune Panthers'), findsOneWidget);
    expect(find.text('45/2 (5.3)'), findsOneWidget);
    expect(find.text('LIVE'), findsOneWidget);
  });

  testWidgets('commentary uses the chosen language', (tester) async {
    final s = await makeState();
    final entries = [
      {'type': 'ball', 'over': '0.1', 'label': '6', 'highlight': 'six', 'is_free_hit': false, 'batter': 'R Mehta', 'bowler': 'S Kale', 'score': '6/0', 'note': '',
        'text': {'en': 'SIX! R Mehta clears the boundary!', 'mr': 'षटकार! R Mehta चा जबरदस्त षटकार!', 'hi': 'छक्का!'}},
    ];
    await tester.pumpWidget(wrap(s, CommentaryList(entries: entries, lang: 'mr')));
    expect(find.textContaining('षटकार'), findsOneWidget);
    expect(find.textContaining('SIX!'), findsNothing);
  });

  testWidgets('ball dots render extras and wickets', (tester) async {
    final s = await makeState();
    await tester.pumpWidget(wrap(s, const Row(children: [BallDot('W'), BallDot('1wd'), BallDot('4')])));
    expect(find.text('W'), findsOneWidget);
    expect(find.text('1wd'), findsOneWidget);
  });
}
