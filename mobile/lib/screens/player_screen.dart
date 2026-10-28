import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';

class PlayerScreen extends StatelessWidget {
  const PlayerScreen({super.key, required this.playerId});
  final int playerId;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    api.track('player');
    return Scaffold(
      appBar: AppBar(title: Text(context.t('stats'))),
      body: AsyncView<Map<String, dynamic>>(
        load: () async => await api.get('/stats/players/$playerId/') as Map<String, dynamic>,
        builder: (context, d, _) {
          final p = d['player'] as Map<String, dynamic>;
          final s = d['stats'] as Map<String, dynamic>;
          final bat = s['batting'] as Map<String, dynamic>;
          final bowl = s['bowling'] as Map<String, dynamic>;
          final field = s['fielding'] as Map<String, dynamic>;
          Widget grid(String title, Map<String, String> items) => Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      for (final e in items.entries)
                        SizedBox(
                          width: 96,
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(e.value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                            Text(e.key, style: Theme.of(context).textTheme.bodySmall),
                          ]),
                        ),
                    ]),
                  ]),
                ),
              );
          return ListView(padding: const EdgeInsets.all(12), children: [
            ListTile(
              leading: const CircleAvatar(radius: 28, child: Icon(Icons.person, size: 32)),
              title: Text('${p['full_name']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
              subtitle: Text('${p['team_name']} · ${p['role']} · ${p['batting_style']} bat${(p['bowling_style'] as String? ?? '').isNotEmpty ? ' · ${p['bowling_style']}' : ''}'),
            ),
            const SizedBox(height: 8),
            grid(context.t('batting'), {
              'Matches': '${s['matches']}', 'Innings': '${bat['innings']}', 'Runs': '${bat['runs']}', 'Highest': '${bat['highest']}',
              'Average': num1(bat['average']), 'Strike rate': num1(bat['strike_rate']), '4s': '${bat['fours']}', '6s': '${bat['sixes']}',
              '50s': '${bat['fifties']}', '100s': '${bat['hundreds']}',
            }),
            grid(context.t('bowling'), {
              'Innings': '${bowl['innings']}', 'Overs': '${bowl['overs']}', 'Wickets': '${bowl['wickets']}', 'Best': '${bowl['best']}',
              'Economy': num1(bowl['economy']), 'Average': num1(bowl['average']), 'Maidens': '${bowl['maidens']}',
            }),
            grid('Fielding', {'Catches': '${field['catches']}', 'Run outs': '${field['run_outs']}', 'Stumpings': '${field['stumpings']}'}),
            if ((d['recent'] as List).isNotEmpty) ...[
              const Padding(padding: EdgeInsets.all(8), child: Text('Recent matches', style: TextStyle(fontWeight: FontWeight.bold))),
              for (final r in d['recent'] as List)
                ListTile(
                  dense: true,
                  title: Text('${r['match']}'),
                  subtitle: Text('${r['tournament']} · ${r['date']}'),
                  trailing: Text('${r['runs']} (${r['balls']})${(r['bowled_balls'] as int) > 0 ? ' · ${r['wickets']} wkt' : ''}'),
                ),
            ],
          ]);
        },
      ),
    );
  }
}
