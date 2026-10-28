import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';
import '../widgets/scorecard.dart';
import 'matches_screen.dart';
import 'team_detail_screen.dart';

class TournamentsScreen extends StatelessWidget {
  const TournamentsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return Scaffold(
      appBar: AppBar(title: Text(context.t('tournaments'))),
      body: AsyncView<List<dynamic>>(
        load: () async => ApiClient.list(await api.get('/tournaments/', query: {'page_size': 100})),
        builder: (context, items, reload) => RefreshIndicator(
          onRefresh: reload,
          child: items.isEmpty
              ? ListView(children: [EmptyView(context.t('nothing'), icon: Icons.emoji_events_outlined)])
              : ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: items.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    final t = items[i] as Map<String, dynamic>;
                    return Card(
                      child: ListTile(
                        leading: const CircleAvatar(child: Icon(Icons.emoji_events)),
                        title: Text('${t['name']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: Text('${t['match_format']} · ${t['ball_type']} · ${t['location']}\n${fmtDate(t['start_date'] as String?)} – ${fmtDate(t['end_date'] as String?)}'
                            '${t['winner_name'] != null ? '\n🏆 ${t['winner_name']}' : ''}'),
                        isThreeLine: true,
                        trailing: (t['live_count'] as int? ?? 0) > 0 ? const LiveDot() : Text('${t['status']}'),
                        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TournamentDetailScreen(tournament: t))),
                      ),
                    );
                  },
                ),
        ),
      ),
    );
  }
}

class TournamentDetailScreen extends StatelessWidget {
  const TournamentDetailScreen({super.key, required this.tournament});
  final Map<String, dynamic> tournament;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final id = tournament['id'];
    api.track('tournament');
    final fg = Theme.of(context).appBarTheme.foregroundColor;
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: Text('${tournament['name']}'),
          bottom: TabBar(
            isScrollable: true,
            labelColor: fg,
            unselectedLabelColor: fg?.withValues(alpha: 0.7),
            indicatorColor: fg,
            tabs: [Tab(text: context.t('fixtures')), Tab(text: context.t('points')), Tab(text: context.t('leaders')), Tab(text: context.t('teams'))],
          ),
        ),
        body: TabBarView(children: [
          MatchList(query: {'tournament': id, 'ordering': 'scheduled_at'}),
          AsyncView<List<dynamic>>(
            load: () async => await api.get('/tournaments/$id/points_table/') as List,
            builder: (context, rows, reload) => RefreshIndicator(onRefresh: reload, child: PointsTable(rows: rows)),
          ),
          AsyncView<Map<String, dynamic>>(
            load: () async => await api.get('/stats/leaderboards/', query: {'tournament': id}) as Map<String, dynamic>,
            builder: (context, data, _) => LeaderboardView(data: data),
          ),
          AsyncView<List<dynamic>>(
            load: () async => await api.get('/tournaments/$id/registrations/') as List,
            builder: (context, regs, _) => ListView(children: [
              for (final r in regs)
                ListTile(
                  leading: TeamBadge(r['team_detail'] as Map<String, dynamic>),
                  title: Text('${r['team_detail']['name']}'),
                  subtitle: Text('${r['group'] != '' ? 'Group ${r['group']} · ' : ''}${(r['players'] as List).length} players'),
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TeamDetailScreen(teamId: r['team'] as int))),
                ),
            ]),
          ),
        ]),
      ),
    );
  }
}

class PointsTable extends StatelessWidget {
  const PointsTable({super.key, required this.rows});
  final List<dynamic> rows;

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) return ListView(children: [EmptyView(context.t('nothing'))]);
    final groups = <String, List<dynamic>>{};
    for (final r in rows) {
      groups.putIfAbsent('${r['group']}', () => []).add(r);
    }
    return ListView(padding: const EdgeInsets.all(12), children: [
      for (final g in groups.entries)
        Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              if (groups.length > 1 || g.key.isNotEmpty) Padding(padding: const EdgeInsets.all(6), child: Text('Group ${g.key}', style: const TextStyle(fontWeight: FontWeight.bold))),
              Table(
                columnWidths: const {0: FlexColumnWidth(3.5)},
                children: [
                  TableRow(children: [for (final h in ['Team', 'P', 'W', 'L', 'T/NR', 'Pts', 'NRR']) _c(h, bold: true)]),
                  for (final r in g.value)
                    TableRow(children: [
                      _c('${r['position']}. ${r['team']['short_name']}', left: true),
                      _c('${r['played']}'), _c('${r['won']}'), _c('${r['lost']}'),
                      _c('${(r['tied'] as int) + (r['no_result'] as int)}'), _c('${r['points']}', bold: true), _c('${r['net_run_rate']}'),
                    ]),
                ],
              ),
            ]),
          ),
        ),
      const Padding(padding: EdgeInsets.all(8), child: Text('NRR = runs scored per over minus runs conceded per over. An all-out side is charged its full quota of overs.', style: TextStyle(fontSize: 11, color: Colors.grey))),
    ]);
  }

  Widget _c(String t, {bool bold = false, bool left = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
        child: Text(t, textAlign: left ? TextAlign.left : TextAlign.center, style: TextStyle(fontSize: 13, fontWeight: bold ? FontWeight.bold : null)),
      );
}
