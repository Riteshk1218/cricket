import 'package:flutter/material.dart';

import '../core/format.dart';
import '../screens/match_detail_screen.dart';
import 'common.dart';

/// Compact card built from the server's match summary payload.
class MatchCard extends StatelessWidget {
  const MatchCard(this.m, {super.key, this.onTap});
  final Map<String, dynamic> m;
  final VoidCallback? onTap;

  String _score(Map<String, dynamic> team) {
    final list = (m['scores'] as Map?)?['${team['id']}'] as List?;
    if (list == null || list.isEmpty) return '';
    return list.map((s) => '${s['runs']}/${s['wickets']} (${s['overs']})${s['is_super_over'] == true ? ' SO' : ''}').join(' & ');
  }

  @override
  Widget build(BuildContext context) {
    final a = m['team_a'] as Map<String, dynamic>;
    final b = m['team_b'] as Map<String, dynamic>;
    final status = m['status'] as String?;
    final live = isLiveStatus(status);
    final batting = m['batting_team_id'];
    Widget row(Map<String, dynamic> t) => Padding(
          padding: const EdgeInsets.symmetric(vertical: 3),
          child: Row(children: [
            TeamBadge(t, size: 28),
            const SizedBox(width: 8),
            Expanded(
              child: Text(t['name'] as String,
                  style: TextStyle(fontWeight: batting == t['id'] ? FontWeight.bold : FontWeight.w500), overflow: TextOverflow.ellipsis),
            ),
            Text(_score(t), style: const TextStyle(fontWeight: FontWeight.bold)),
          ]),
        );
    return Card(
      child: InkWell(
        onTap: onTap ?? () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => MatchDetailScreen(matchId: m['id'] as int))),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(
                child: Text('${(m['tournament'] as Map?)?['name'] ?? ''} · #${m['match_number']} ${m['stage'] == 'league' ? '' : (m['stage'] as String).toUpperCase()}',
                    style: Theme.of(context).textTheme.bodySmall, overflow: TextOverflow.ellipsis),
              ),
              if (live) LiveDot(label: status == 'live' ? 'LIVE' : (statusLabels[status] ?? '').toUpperCase()),
            ]),
            const SizedBox(height: 6),
            row(a),
            row(b),
            const SizedBox(height: 4),
            Text(
              m['result'] as String? ??
                  (m['target'] != null ? 'Target ${m['target']}' : (live ? '' : '${statusLabels[status] ?? status} · ${fmtDateTime(m['scheduled_at'] as String?)}')),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.primary, fontWeight: FontWeight.w600),
            ),
          ]),
        ),
      ),
    );
  }
}
