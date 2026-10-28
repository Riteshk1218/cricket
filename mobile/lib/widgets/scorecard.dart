import 'package:flutter/material.dart';

import '../core/format.dart';
import '../core/i18n.dart';
import 'common.dart';

class InningsCard extends StatelessWidget {
  const InningsCard({super.key, required this.inn});
  final Map<String, dynamic> inn;

  @override
  Widget build(BuildContext context) {
    final small = Theme.of(context).textTheme.bodySmall;
    final ex = inn['extras'] as Map<String, dynamic>;
    TableRow head(List<String> cells) => TableRow(
        decoration: BoxDecoration(color: Theme.of(context).colorScheme.surfaceContainerHighest),
        children: [for (final c in cells) Padding(padding: const EdgeInsets.all(6), child: Text(c, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)))]);
    Widget cell(String t, {bool bold = false, TextAlign align = TextAlign.right}) =>
        Padding(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 5), child: Text(t, textAlign: align, style: TextStyle(fontSize: 13, fontWeight: bold ? FontWeight.bold : null)));
    const widths = {0: FlexColumnWidth(3.2), 1: FlexColumnWidth(1), 2: FlexColumnWidth(1), 3: FlexColumnWidth(0.8), 4: FlexColumnWidth(0.8), 5: FlexColumnWidth(1.3)};
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            TeamBadge(inn['batting_team'] as Map<String, dynamic>, size: 28),
            const SizedBox(width: 8),
            Expanded(child: Text('${inn['batting_team']['name']}${inn['is_super_over'] == true ? ' · Super over' : ''}', style: const TextStyle(fontWeight: FontWeight.bold))),
            Text('${inn['total']}/${inn['wickets']} (${inn['overs']})', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          ]),
          if (inn['target'] != null) Text('${context.t('target')} ${inn['target']}', style: small),
          const SizedBox(height: 8),
          Table(columnWidths: widths, children: [
            head([context.t('batting'), 'R', 'B', '4s', '6s', 'SR']),
            for (final b in inn['batting'] as List)
              TableRow(children: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 5),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${b['name']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                    Text('${b['dismissal_text']}', style: small),
                  ]),
                ),
                cell('${b['runs']}', bold: true), cell('${b['balls']}'), cell('${b['fours']}'), cell('${b['sixes']}'), cell(num1(b['strike_rate'])),
              ]),
          ]),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 6),
            child: Text('${context.t('extras')}: ${ex['total']} (wd ${ex['wides']}, nb ${ex['noballs']}, b ${ex['byes']}, lb ${ex['legbyes']}, p ${ex['penalty']})', style: small),
          ),
          if ((inn['yet_to_bat'] as List).isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6),
              child: Text('${context.t('yet_to_bat')}: ${(inn['yet_to_bat'] as List).map((p) => p['name']).join(', ')}', style: small),
            ),
          const SizedBox(height: 10),
          Table(columnWidths: widths, children: [
            head([context.t('bowling'), 'O', 'M', 'R', 'W', 'Econ']),
            for (final b in inn['bowling'] as List)
              TableRow(children: [
                cell('${b['name']}', align: TextAlign.left), cell('${b['overs']}'), cell('${b['maidens']}'), cell('${b['runs']}'), cell('${b['wickets']}', bold: true), cell(num1(b['economy'])),
              ]),
          ]),
          if ((inn['fall_of_wickets'] as List).isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(context.t('fow'), style: const TextStyle(fontWeight: FontWeight.bold)),
            Text((inn['fall_of_wickets'] as List).map((f) => '${f['score']}-${f['wicket']} (${f['player']}, ${f['overs']})').join(' · '), style: small),
          ],
        ]),
      ),
    );
  }
}

class OversList extends StatelessWidget {
  const OversList({super.key, required this.inn});
  final Map<String, dynamic> inn;
  @override
  Widget build(BuildContext context) {
    final overs = (inn['overs_detail'] as List).reversed.toList();
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(padding: const EdgeInsets.all(12), child: Text('${inn['batting_team']['name']}${inn['is_super_over'] == true ? ' · Super over' : ''}', style: const TextStyle(fontWeight: FontWeight.bold))),
        for (final o in overs)
          ListTile(
            dense: true,
            leading: CircleAvatar(radius: 14, child: Text('${o['number']}', style: const TextStyle(fontSize: 12))),
            title: SingleChildScrollView(scrollDirection: Axis.horizontal, child: Row(children: [for (final b in o['balls'] as List) BallDot('$b', size: 26)])),
            subtitle: Text('${o['bowler']} · ${o['runs']} runs${(o['wickets'] as int) > 0 ? ', ${o['wickets']} wkt' : ''}${o['score_at_end'] != '' ? ' · ${o['score_at_end']}' : ''}'),
          ),
        if (overs.isEmpty) const Padding(padding: EdgeInsets.all(12), child: Text('-')),
      ]),
    );
  }
}

class CommentaryList extends StatelessWidget {
  const CommentaryList({super.key, required this.entries, required this.lang});
  final List<dynamic> entries;
  final String lang;

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) return EmptyView(context.t('nothing'), icon: Icons.mic_none);
    return Column(children: [
      for (final e in entries)
        if (e['type'] == 'ball')
          ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 4),
            leading: SizedBox(
              width: 52,
              child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Text('${e['over']}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 2),
                BallDot('${e['label']}', size: 24),
              ]),
            ),
            title: Text('${(e['text'] as Map)[lang] ?? (e['text'] as Map)['en']}',
                style: TextStyle(fontWeight: e['highlight'] != null ? FontWeight.bold : null)),
            subtitle: Text('${e['bowler']} to ${e['batter']} · ${e['score']}${e['is_free_hit'] == true ? ' · FREE HIT' : ''}${(e['note'] as String? ?? '').isNotEmpty ? '\n${e['note']}' : ''}'),
          )
        else
          Container(
            width: double.infinity,
            margin: const EdgeInsets.symmetric(vertical: 4),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: Theme.of(context).colorScheme.secondaryContainer, borderRadius: BorderRadius.circular(8)),
            child: Text('${(e['text'] as Map)[lang] ?? (e['text'] as Map)['en']}', style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
    ]);
  }
}

class LeaderboardView extends StatelessWidget {
  const LeaderboardView({super.key, required this.data});
  final Map<String, dynamic> data;
  static const titles = {
    'most_runs': 'Most runs', 'most_wickets': 'Most wickets', 'highest_scores': 'Highest scores',
    'highest_strike_rate': 'Best strike rate', 'best_economy': 'Best economy', 'most_sixes': 'Most sixes',
    'most_fours': 'Most fours', 'most_catches': 'Most catches',
  };
  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(12), children: [
      for (final entry in titles.entries)
        if ((data[entry.key] as List?)?.isNotEmpty == true)
          Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Padding(padding: const EdgeInsets.all(12), child: Text(entry.value, style: const TextStyle(fontWeight: FontWeight.bold))),
              for (final (i, r) in (data[entry.key] as List).take(5).indexed)
                ListTile(dense: true, leading: Text('${i + 1}'), title: Text('${r['name']}'), subtitle: Text('${r['team']}'), trailing: Text('${r['value']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16))),
            ]),
          ),
      if (titles.keys.every((k) => (data[k] as List?)?.isEmpty ?? true)) EmptyView(context.t('nothing')),
    ]);
  }
}
