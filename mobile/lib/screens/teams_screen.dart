import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';
import 'team_detail_screen.dart';

class TeamsScreen extends StatelessWidget {
  const TeamsScreen({super.key});
  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return Scaffold(
      appBar: AppBar(title: Text(context.t('teams'))),
      body: AsyncView<List<dynamic>>(
        load: () async => ApiClient.list(await api.get('/teams/', query: {'page_size': 500})),
        builder: (context, teams, reload) => RefreshIndicator(
          onRefresh: reload,
          child: ListView(children: [
            for (final t in teams)
              ListTile(
                leading: TeamBadge(t as Map<String, dynamic>),
                title: Text('${t['name']}'),
                subtitle: Text('${t['city']} · ${t['player_count']} players'),
                onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => TeamDetailScreen(teamId: t['id'] as int))),
              ),
            if (teams.isEmpty) EmptyView(context.t('nothing')),
          ]),
        ),
      ),
    );
  }
}
