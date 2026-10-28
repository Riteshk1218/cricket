import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';
import 'matches_screen.dart';
import 'player_screen.dart';

class TeamDetailScreen extends StatelessWidget {
  const TeamDetailScreen({super.key, required this.teamId});
  final int teamId;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final fg = Theme.of(context).appBarTheme.foregroundColor;
    return AsyncView<List<dynamic>>(
      load: () => Future.wait([api.get('/teams/$teamId/'), api.get('/teams/$teamId/players/'), api.get('/stats/teams/$teamId/')]),
      builder: (context, d, _) {
        final team = d[0] as Map<String, dynamic>;
        final players = ApiClient.list(d[1]);
        final st = d[2] as Map<String, dynamic>;
        return DefaultTabController(
          length: 2,
          child: Scaffold(
            appBar: AppBar(
              title: Text('${team['name']}'),
              bottom: TabBar(labelColor: fg, unselectedLabelColor: fg?.withValues(alpha: 0.7), indicatorColor: fg, tabs: [Tab(text: context.t('players')), Tab(text: context.t('matches'))]),
            ),
            body: TabBarView(children: [
              ListView(children: [
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(children: [
                    TeamBadge(team, size: 56),
                    const SizedBox(width: 16),
                    Expanded(child: Text('Played ${st['played']} · Won ${st['won']} · Lost ${st['lost']} · Tied ${st['tied']} · NR ${st['no_result']}'
                        '${st['highest_total'] != null ? '\nHighest total ${st['highest_total']['runs']}/${st['highest_total']['wickets']}' : ''}')),
                  ]),
                ),
                const Divider(),
                for (final p in players)
                  ListTile(
                    leading: CircleAvatar(child: Text('${p['jersey_number'] ?? ''}')),
                    title: Text('${p['full_name']}'),
                    subtitle: Text('${p['role']} · ${p['batting_style']} bat${(p['bowling_style'] as String? ?? '').isNotEmpty ? ' · ${p['bowling_style']}' : ''}'),
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PlayerScreen(playerId: p['id'] as int))),
                  ),
              ]),
              MatchList(query: {'team': teamId, 'ordering': '-scheduled_at'}),
            ]),
          ),
        );
      },
    );
  }
}
