import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/app_state.dart';
import '../core/format.dart';
import '../core/i18n.dart';
import '../core/live_socket.dart';
import '../core/sound.dart';
import '../widgets/celebration_overlay.dart';
import '../widgets/common.dart';
import '../widgets/scorecard.dart';
import 'scorer_panel_screen.dart';

/// Live match centre. Receives a full snapshot over WebSocket after every ball.
class MatchDetailScreen extends StatefulWidget {
  const MatchDetailScreen({super.key, required this.matchId});
  final int matchId;
  @override
  State<MatchDetailScreen> createState() => _MatchDetailScreenState();
}

class _MatchDetailScreenState extends State<MatchDetailScreen> {
  Map<String, dynamic>? _snap;
  String? _error;
  int _viewers = 0;
  LiveSocket? _socket;
  SocketStatus _status = SocketStatus.connecting;
  String? _celebration;
  int? _lastCelebrated;
  bool _canScore = false;

  @override
  void initState() {
    super.initState();
    _load();
    final s = context.read<AppState>();
    final api = context.read<ApiClient>();
    api.track('match', matchId: widget.matchId);
    _socket = LiveSocket('${s.wsUrl}/ws/matches/${widget.matchId}/?client=${api.clientType}', onMessage: _onMessage, onStatus: (st) {
      if (mounted) setState(() => _status = st);
    })
      ..connect();
    if (s.canScore) {
      api.get('/matches/${widget.matchId}/permissions_info/').then((r) {
        if (mounted) setState(() => _canScore = r['can_score'] == true);
      }).catchError((_) {});
    }
  }

  Future<void> _load() async {
    try {
      final d = await context.read<ApiClient>().get('/matches/${widget.matchId}/live/') as Map<String, dynamic>;
      _apply(d, celebrate: false);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  void _apply(Map<String, dynamic> snap, {Map<String, dynamic>? event, bool celebrate = true}) {
    if (!mounted) return;
    final current = _snap?['version'] as int? ?? -1;
    if ((snap['version'] as int? ?? 0) < current) return; // stale message after a reconnect
    String? burst;
    final id = event?['delivery_id'] as int?;
    if (celebrate && event != null && event['highlight'] != null && id != _lastCelebrated && (snap['version'] as int) > current) {
      burst = event['highlight'] as String;
      _lastCelebrated = id;
      context.read<SoundPlayer>().play(burst);
    }
    setState(() {
      _snap = snap;
      _error = null;
      if (burst != null && context.read<AppState>().animations) _celebration = burst;
    });
  }

  void _onMessage(Map<String, dynamic> msg) {
    switch (msg['type']) {
      case 'snapshot':
        _apply(Map<String, dynamic>.from(msg['snapshot'] as Map), celebrate: false);
        if (msg['viewers'] != null && mounted) setState(() => _viewers = msg['viewers'] as int);
      case 'update':
        _apply(Map<String, dynamic>.from(msg['snapshot'] as Map), event: msg['event'] == null ? null : Map<String, dynamic>.from(msg['event'] as Map));
      case 'viewers':
        if (mounted) setState(() => _viewers = msg['count'] as int);
    }
  }

  @override
  void dispose() {
    _socket?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final snap = _snap;
    final lang = context.watch<AppState>().language;
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: Text(snap == null ? '' : '${snap['team_a']['short_name']} vs ${snap['team_b']['short_name']}'),
          actions: [
            if (snap != null)
              Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Row(children: [
                    Icon(Icons.circle, size: 9, color: _status == SocketStatus.open ? Colors.lightGreenAccent : Colors.orange),
                    const SizedBox(width: 4),
                    Text('$_viewers 👁', style: const TextStyle(fontSize: 13)),
                  ]),
                ),
              ),
            if (_canScore)
              IconButton(
                tooltip: context.t('scorer'),
                icon: const Icon(Icons.edit_note),
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => ScorerPanelScreen(matchId: widget.matchId))),
              ),
          ],
          bottom: TabBar(
            isScrollable: true,
            labelColor: Theme.of(context).appBarTheme.foregroundColor,
            unselectedLabelColor: Theme.of(context).appBarTheme.foregroundColor?.withValues(alpha: 0.7),
            indicatorColor: Theme.of(context).appBarTheme.foregroundColor,
            tabs: [Tab(text: context.t('live')), Tab(text: context.t('scorecard')), Tab(text: context.t('commentary')), Tab(text: context.t('overs'))],
          ),
        ),
        body: Stack(children: [
          if (snap == null)
            _error != null ? ErrorView(_error!, onRetry: _load) : const Center(child: CircularProgressIndicator())
          else
            Column(children: [
              if (_status != SocketStatus.open)
                Container(
                  width: double.infinity,
                  color: Colors.orange.withValues(alpha: 0.2),
                  padding: const EdgeInsets.all(6),
                  child: Text(context.t('reconnecting'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 12)),
                ),
              Expanded(
                child: TabBarView(children: [
                  RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.all(12), children: [LivePanel(snap: snap), const SizedBox(height: 12), CommentaryList(entries: (snap['commentary'] as List).take(8).toList(), lang: lang)])),
                  ListView(padding: const EdgeInsets.all(12), children: [for (final inn in (snap['innings'] as List).reversed) InningsCard(inn: inn as Map<String, dynamic>)]),
                  _FullCommentary(matchId: widget.matchId, version: snap['version'] as int, lang: lang),
                  ListView(padding: const EdgeInsets.all(12), children: [for (final inn in (snap['innings'] as List).reversed) OversList(inn: inn as Map<String, dynamic>)]),
                ]),
              ),
            ]),
          if (_celebration != null)
            Positioned.fill(
              child: CelebrationOverlay(
                key: ValueKey(_lastCelebrated),
                kind: _celebration!,
                label: tr(lang, _celebration!),
                onDone: () {
                  if (mounted) setState(() => _celebration = null);
                },
              ),
            ),
        ]),
      ),
    );
  }
}

/// Live summary: score, batters at the crease, bowler, this over, equation.
class LivePanel extends StatelessWidget {
  const LivePanel({super.key, required this.snap});
  final Map<String, dynamic> snap;

  @override
  Widget build(BuildContext context) {
    final c = snap['current'] as Map<String, dynamic>?;
    final result = snap['result'] as Map<String, dynamic>?;
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${snap['tournament']['name']} · #${snap['match_number']}', style: theme.textTheme.bodySmall),
          if (snap['ground'] != null) Text('${snap['ground']}', style: theme.textTheme.bodySmall),
          const SizedBox(height: 8),
          for (final inn in snap['innings'] as List)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(children: [
                TeamBadge(inn['batting_team'] as Map<String, dynamic>, size: 26),
                const SizedBox(width: 8),
                Expanded(child: Text('${inn['batting_team']['name']}${inn['is_super_over'] == true ? ' (Super over)' : ''}')),
                Text('${inn['total']}/${inn['wickets']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                Text('  (${inn['overs']})', style: theme.textTheme.bodySmall),
              ]),
            ),
          if ((snap['innings'] as List).isEmpty)
            Text(snap['toss']?['text'] as String? ?? '${statusLabels[snap['status']] ?? snap['status']} · ${fmtDateTime(snap['scheduled_at'] as String?)}'),
          if (snap['status'] == 'paused')
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('⏸ ${context.t('paused')}: ${snap['clock']?['pause_reason'] ?? ''}', style: const TextStyle(color: Colors.orange, fontWeight: FontWeight.bold)),
            ),
          if (result != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('${result['summary']}${result['player_of_match_name'] != null ? '\nPlayer of the match: ${result['player_of_match_name']}' : ''}',
                  style: TextStyle(color: theme.colorScheme.primary, fontWeight: FontWeight.bold)),
            ),
          if (c != null && c['in_progress'] == true) ...[
            const Divider(height: 20),
            Row(children: [
              Text('${context.t('crr')} ${num1(c['run_rate'])}', style: theme.textTheme.bodySmall),
              if (c['required_run_rate'] != null) Text('   ${context.t('rrr')} ${num1(c['required_run_rate'])}', style: theme.textTheme.bodySmall),
              const Spacer(),
              if (c['powerplay']?['active'] == true) Chip(label: Text('PP ${c['powerplay']['overs']}'), visualDensity: VisualDensity.compact),
              if (c['free_hit'] == true) Padding(padding: const EdgeInsets.only(left: 6), child: LiveDot(label: context.t('free_hit'))),
            ]),
            if (c['equation'] != null) Text('${c['equation']}', style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            for (final b in [c['striker'], c['non_striker']])
              if (b != null)
                Row(children: [
                  Expanded(child: Text('${b['name']}${b['player_id'] == c['striker']?['player_id'] ? ' *' : ''}', style: const TextStyle(fontWeight: FontWeight.w600))),
                  Text('${b['runs']} (${b['balls']})  4s ${b['fours']}  6s ${b['sixes']}'),
                ]),
            if (c['partnership'] != null) Text('Partnership ${c['partnership']['runs']} (${c['partnership']['balls']})', style: theme.textTheme.bodySmall),
            const SizedBox(height: 6),
            if (c['bowler'] != null)
              Row(children: [
                const Icon(Icons.sports_baseball, size: 14),
                const SizedBox(width: 4),
                Expanded(child: Text('${c['bowler']['name']}', style: const TextStyle(fontWeight: FontWeight.w600))),
                Text('${c['bowler']['overs']}-${c['bowler']['maidens']}-${c['bowler']['runs']}-${c['bowler']['wickets']}'),
              ]),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(children: [
                Text('This over: ', style: theme.textTheme.bodySmall),
                for (final ball in (c['this_over']?['balls'] as List? ?? [])) BallDot('$ball'),
              ]),
            ),
          ],
        ]),
      ),
    );
  }
}

class _FullCommentary extends StatefulWidget {
  const _FullCommentary({required this.matchId, required this.version, required this.lang});
  final int matchId;
  final int version;
  final String lang;
  @override
  State<_FullCommentary> createState() => _FullCommentaryState();
}

class _FullCommentaryState extends State<_FullCommentary> {
  List<dynamic>? _entries;
  int? _loadedVersion;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reload();
  }

  @override
  void didUpdateWidget(covariant _FullCommentary old) {
    super.didUpdateWidget(old);
    if (widget.version != _loadedVersion) _reload();
  }

  Future<void> _reload() async {
    _loadedVersion = widget.version;
    try {
      final r = await context.read<ApiClient>().get('/matches/${widget.matchId}/commentary/');
      if (mounted) setState(() => _entries = r as List);
    } catch (_) {
      if (mounted) setState(() => _entries ??= []);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_entries == null) return const Center(child: CircularProgressIndicator());
    return ListView(padding: const EdgeInsets.all(12), children: [CommentaryList(entries: _entries!, lang: widget.lang)]);
  }
}
