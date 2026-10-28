import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../core/i18n.dart';
import 'auth_screen.dart';
import 'home_screen.dart';
import 'matches_screen.dart';
import 'players_screen.dart';
import 'profile_screen.dart';
import 'scorer_home_screen.dart';
import 'settings_screen.dart';
import 'teams_screen.dart';
import 'tournaments_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [const HomeScreen(), const MatchesScreen(), const TournamentsScreen(), const MoreScreen()];
    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home_outlined), selectedIcon: const Icon(Icons.home), label: context.t('home')),
          NavigationDestination(icon: const Icon(Icons.sports_cricket_outlined), selectedIcon: const Icon(Icons.sports_cricket), label: context.t('matches')),
          NavigationDestination(icon: const Icon(Icons.emoji_events_outlined), selectedIcon: const Icon(Icons.emoji_events), label: context.t('tournaments')),
          NavigationDestination(icon: const Icon(Icons.menu), label: context.t('more')),
        ],
      ),
    );
  }
}

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final s = context.watch<AppState>();
    void open(Widget w) => Navigator.of(context).push(MaterialPageRoute(builder: (_) => w));
    return Scaffold(
      appBar: AppBar(title: Text(context.t('more'))),
      body: ListView(children: [
        ListTile(
          leading: CircleAvatar(child: Icon(s.loggedIn ? Icons.person : Icons.person_outline)),
          title: Text(s.loggedIn ? '${s.user?['display_name'] ?? s.user?['username']}' : context.t('guest')),
          subtitle: Text(s.loggedIn ? s.role.replaceAll('_', ' ') : context.t('login')),
          onTap: () => open(s.loggedIn ? const ProfileScreen() : const AuthScreen()),
        ),
        const Divider(),
        if (s.canScore)
          ListTile(leading: const Icon(Icons.edit_note), title: Text(context.t('my_matches')), onTap: () => open(const ScorerHomeScreen())),
        ListTile(leading: const Icon(Icons.shield_outlined), title: Text(context.t('teams')), onTap: () => open(const TeamsScreen())),
        ListTile(leading: const Icon(Icons.people_outline), title: Text(context.t('players')), onTap: () => open(const PlayersScreen())),
        ListTile(leading: const Icon(Icons.fact_check_outlined), title: Text(context.t('results')), onTap: () => open(const MatchesScreen(initialTab: 2, standalone: true))),
        ListTile(leading: const Icon(Icons.settings_outlined), title: Text(context.t('settings')), onTap: () => open(const SettingsScreen())),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Text('Server: ${s.serverUrl}', style: Theme.of(context).textTheme.bodySmall),
        ),
      ]),
    );
  }
}
