import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';
import '../widgets/match_card.dart';
import 'scorer_panel_screen.dart';

/// Matches the logged-in scorer is assigned to (admins see matches they manage).
class ScorerHomeScreen extends StatelessWidget {
  const ScorerHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return Scaffold(
      appBar: AppBar(title: Text(context.t('my_matches'))),
      body: AsyncView<List<dynamic>>(
        load: () async => ApiClient.list(await api.get('/matches/', query: {'assigned': 1, 'page_size': 200, 'ordering': 'scheduled_at'}))
            .where((m) => !const ['completed', 'abandoned'].contains(m['status']))
            .toList(),
        builder: (context, items, reload) => RefreshIndicator(
          onRefresh: reload,
          child: items.isEmpty
              ? ListView(children: const [EmptyView('No matches are assigned to you. Ask a tournament admin to assign you on the website.')])
              : ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: items.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (_, i) => MatchCard(
                    items[i] as Map<String, dynamic>,
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ScorerPanelScreen(matchId: items[i]['id'] as int))),
                  ),
                ),
        ),
      ),
    );
  }
}
