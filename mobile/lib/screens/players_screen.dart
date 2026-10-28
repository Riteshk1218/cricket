import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';
import 'player_screen.dart';

class PlayersScreen extends StatefulWidget {
  const PlayersScreen({super.key});
  @override
  State<PlayersScreen> createState() => _PlayersScreenState();
}

class _PlayersScreenState extends State<PlayersScreen> {
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return Scaffold(
      appBar: AppBar(title: Text(context.t('players'))),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(
            decoration: InputDecoration(prefixIcon: const Icon(Icons.search), hintText: context.t('search'), isDense: true),
            onSubmitted: (v) => setState(() => _q = v.trim()),
          ),
        ),
        Expanded(
          child: AsyncView<List<dynamic>>(
            key: ValueKey(_q),
            load: () async => ApiClient.list(await api.get('/players/', query: {'page_size': 200, if (_q.isNotEmpty) 'search': _q})),
            builder: (context, players, _) => players.isEmpty
                ? EmptyView(context.t('nothing'))
                : ListView.builder(
                    itemCount: players.length,
                    itemBuilder: (_, i) {
                      final p = players[i];
                      return ListTile(
                        leading: const CircleAvatar(child: Icon(Icons.person)),
                        title: Text('${p['full_name']}'),
                        subtitle: Text('${p['team_name']} · ${p['role']}'),
                        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => PlayerScreen(playerId: p['id'] as int))),
                      );
                    },
                  ),
          ),
        ),
      ]),
    );
  }
}
