import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:uuid/uuid.dart';

import '../core/api_client.dart';
import '../core/app_state.dart';
import '../core/format.dart';
import '../core/live_socket.dart';
import '../core/theme.dart';
import '../widgets/common.dart';

/// Ball-by-ball scoring on the phone. Every action goes to the server, which
/// validates it, stores it and broadcasts the new snapshot to all viewers.
/// Ball edits, rain revisions and manual results are done on the website panel.
class ScorerPanelScreen extends StatefulWidget {
  const ScorerPanelScreen({super.key, required this.matchId});
  final int matchId;
  @override
  State<ScorerPanelScreen> createState() => _ScorerPanelScreenState();
}

class _ScorerPanelScreenState extends State<ScorerPanelScreen> {
  Map<String, dynamic>? _snap;
  bool? _canScore;
  String? _error;
  bool _busy = false;
  LiveSocket? _socket;
  SocketStatus _status = SocketStatus.connecting;
  String? _prompted; // avoids opening the same batter/bowler prompt twice

  ApiClient get _api => context.read<ApiClient>();
  String get _base => '/matches/${widget.matchId}';

  @override
  void initState() {
    super.initState();
    _load();
    _api.get('$_base/permissions_info/').then((r) {
      if (mounted) setState(() => _canScore = r['can_score'] == true);
    }).catchError((e) {
      if (mounted) setState(() => _canScore = false);
    });
    final s = context.read<AppState>();
    _socket = LiveSocket('${s.wsUrl}/ws/matches/${widget.matchId}/?client=scorer', onMessage: (m) {
      if (m['snapshot'] != null) _apply(Map<String, dynamic>.from(m['snapshot'] as Map));
    }, onStatus: (st) {
      if (mounted) setState(() => _status = st);
    })
      ..connect();
  }

  @override
  void dispose() {
    _socket?.close();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      _apply(await _api.get('$_base/live/') as Map<String, dynamic>, force: true);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  void _apply(Map<String, dynamic> snap, {bool force = false}) {
    if (!mounted) return;
    if (!force && _snap != null && (snap['version'] as int) < (_snap!['version'] as int)) return;
    setState(() {
      _snap = snap;
      _error = null;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) => _autoPrompt());
  }

  Future<bool> _call(String action, [Map<String, dynamic>? body]) async {
    if (_busy) return false;
    setState(() => _busy = true);
    try {
      final r = await _api.post('$_base/score/$action/', body ?? {});
      if (r is Map && r['snapshot'] != null) _apply(Map<String, dynamic>.from(r['snapshot'] as Map), force: true);
      return true;
    } on ApiException catch (e) {
      if (e.isConflict) await _load();
      _toast(e.isConflict ? 'Another update arrived first. The score has been refreshed; please check and try again.' : e.message, error: true);
      return false;
    } catch (e) {
      _toast('$e', error: true);
      return false;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _toast(String msg, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg), backgroundColor: error ? ballRed : null));
  }

  Map<String, dynamic>? get _c => _snap?['current'] as Map<String, dynamic>?;
  bool get _live => _snap?['status'] == 'live' && _c?['in_progress'] == true;

  List<Map<String, dynamic>> _squad(dynamic teamId) =>
      ((_snap?['squads'] as Map?)?['$teamId'] as List? ?? []).cast<Map<String, dynamic>>();

  Map<String, dynamic>? get _currentInnings {
    final c = _c;
    if (c == null) return null;
    return (_snap!['innings'] as List).cast<Map<String, dynamic>>().firstWhere((i) => i['id'] == c['innings_id']);
  }

  void _autoPrompt() {
    final c = _c;
    if (!_live || c == null || _busy) return;
    final key = '${_snap!['version']}';
    if (_prompted == key) return;
    if (c['need_batter'] == true) {
      _prompted = key;
      _newBatter();
    } else if (c['need_bowler'] == true) {
      _prompted = key;
      _newBowler();
    }
  }

  // --- dialogs ---------------------------------------------------------------
  Future<int?> _pickPlayer(String title, List<Map<String, dynamic>> players, {String Function(Map<String, dynamic>)? subtitle}) {
    return showModalBottomSheet<int>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.of(ctx).size.height * 0.7),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Padding(padding: const EdgeInsets.all(16), child: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16))),
            if (players.isEmpty) const Padding(padding: EdgeInsets.all(16), child: Text('No players available.')),
            Flexible(
              child: ListView(shrinkWrap: true, children: [
                for (final p in players)
                  ListTile(title: Text('${p['name']}'), subtitle: subtitle == null ? null : Text(subtitle(p)), onTap: () => Navigator.pop(ctx, p['player_id'] as int)),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Future<bool> _confirm(String title, String message) async =>
      await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(title: Text(title), content: Text(message), actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Confirm')),
        ]),
      ) ??
      false;

  Future<void> _newBatter() async {
    final c = _c!;
    final inn = _currentInnings!;
    final out = (inn['batting'] as List).where((b) => b['is_out'] == true).map((b) => b['player_id']).toSet();
    final atCrease = {c['striker']?['player_id'], c['non_striker']?['player_id']};
    final available = _squad(c['batting_team']['id']).where((p) => !out.contains(p['player_id']) && !atCrease.contains(p['player_id'])).toList();
    final end = c['striker'] == null ? 'striker' : 'non_striker';
    final id = await _pickPlayer('New batter (${end == 'striker' ? 'on strike' : 'non-striker'})', available);
    if (id != null) await _call('batter', {'player': id, 'end': end});
  }

  Future<void> _newBowler({bool midOver = false}) async {
    final c = _c!;
    final inn = _currentInnings!;
    final rules = _snap!['rules'] as Map<String, dynamic>;
    final bpo = rules['balls_per_over'] as int;
    final maxBalls = ((rules['max_overs_per_bowler'] as int?) ?? 0) * bpo;
    final balls = {for (final b in inn['bowling'] as List) b['player_id']: b['balls'] as int};
    // Law 17.8: the previous over's bowler may not bowl any part of this over.
    final blocked = rules['consecutive_overs_allowed'] == true ? null : c['last_over_bowler'];
    final list = _squad(c['bowling_team']['id'])
        .where((p) => p['player_id'] != blocked && p['player_id'] != (midOver ? (c['bowler']?['player_id']) : null) && (maxBalls == 0 || (balls[p['player_id']] ?? 0) < maxBalls))
        .toList();
    final id = await _pickPlayer(midOver ? 'Change bowler mid-over' : 'Bowler for the next over', list,
        subtitle: (p) => '${overs(balls[p['player_id']] ?? 0, bpo)} overs bowled');
    if (id == null) return;
    await _call('bowler', {'bowler': id, 'mid_over': midOver, if (midOver) 'reason': 'Bowler change (injury/other)'});
  }

  String overs(int balls, int bpo) => '${balls ~/ bpo}.${balls % bpo}';

  Future<void> _ball(Map<String, dynamic> payload) async {
    final c = _c!;
    await _call('delivery', {'client_event_id': const Uuid().v4(), 'expected_sequence': (c['last_sequence'] as int? ?? 0) + 1, ...payload});
  }

  Future<void> _extras(String kind) async {
    final payload = await showModalBottomSheet<Map<String, dynamic>>(context: context, builder: (_) => _ExtrasSheet(kind: kind));
    if (payload != null) await _ball(payload);
  }

  Future<void> _wicket() async {
    final payload = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _WicketSheet(current: _c!, fielders: _squad(_c!['bowling_team']['id']), disallowed: ((_snap!['rules'] as Map)['disallowed_dismissals'] as List? ?? []).cast<String>()),
    );
    if (payload != null) await _ball(payload);
  }

  Future<void> _undo() async {
    final inns = _snap!['innings'] as List;
    if (inns.isEmpty) return;
    if (await _confirm('Undo last ball?', 'The last recorded action is removed and the innings is replayed. It stays in the correction history.')) {
      await _call('undo', {'reason': 'Undo by scorer (mobile)', 'expected_sequence': inns.last['last_sequence']});
    }
  }

  Future<void> _pause() async {
    final ctrl = TextEditingController(text: 'Rain');
    final reason = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Pause match'),
        content: TextField(controller: ctrl, decoration: const InputDecoration(labelText: 'Reason')),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')), FilledButton(onPressed: () => Navigator.pop(ctx, ctrl.text), child: const Text('Pause'))],
      ),
    );
    if (reason != null) await _call('pause', {'reason': reason});
  }

  Future<void> _retire() async {
    final c = _c!;
    final id = await _pickPlayer('Retire hurt', [c['striker'], c['non_striker']].whereType<Map<String, dynamic>>().map((b) => {'player_id': b['player_id'], 'name': b['name']}).toList());
    if (id != null) await _call('retire', {'player': id, 'kind': 'retired_hurt'});
  }

  // --- build -----------------------------------------------------------------
  @override
  Widget build(BuildContext context) {
    final snap = _snap;
    Widget body;
    if (snap == null || _canScore == null) {
      body = _error != null ? ErrorView(_error!, onRetry: _load) : const Center(child: CircularProgressIndicator());
    } else if (_canScore == false) {
      body = const ErrorView('You are not assigned to score this match.');
    } else {
      body = _buildStage(snap);
    }
    return Scaffold(
      appBar: AppBar(
        title: Text(snap == null ? 'Scorer' : 'Score: ${snap['team_a']['short_name']} v ${snap['team_b']['short_name']}'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Icon(_status == SocketStatus.open ? Icons.cloud_done : Icons.cloud_off, color: _status == SocketStatus.open ? Colors.lightGreenAccent : Colors.orange),
          ),
        ],
      ),
      body: Stack(children: [body, if (_busy) const LinearProgressIndicator()]),
    );
  }

  Widget _buildStage(Map<String, dynamic> snap) {
    final status = snap['status'] as String;
    final a = snap['team_a'] as Map<String, dynamic>;
    final b = snap['team_b'] as Map<String, dynamic>;
    if (const ['completed', 'abandoned'].contains(status)) {
      return EmptyView('${snap['result']?['summary'] ?? statusLabels[status]}', icon: Icons.emoji_events);
    }
    if (_squad(a['id']).isEmpty || _squad(b['id']).isEmpty) {
      return _SquadSetup(snap: snap, call: _call);
    }
    if (snap['toss'] == null) return _TossCard(snap: snap, call: _call);
    if (status == 'paused') {
      return ListView(padding: const EdgeInsets.all(16), children: [
        _scoreHeader(),
        const SizedBox(height: 16),
        Text('Match paused: ${snap['clock']?['pause_reason'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        FilledButton.icon(onPressed: () => _call('resume'), icon: const Icon(Icons.play_arrow), label: const Text('Resume')),
      ]);
    }
    if (_c == null || _c!['in_progress'] != true) return _StartInnings(snap: snap, call: _call);
    return _livePad();
  }

  Widget _scoreHeader() {
    final c = _c;
    if (c == null) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${c['batting_team']['name']}', style: const TextStyle(fontWeight: FontWeight.bold))),
            Text('${c['score']}', style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900)),
            Text('  (${c['overs']})'),
          ]),
          if (c['equation'] != null) Text('${c['equation']}'),
          if (c['free_hit'] == true) const Padding(padding: EdgeInsets.only(top: 4), child: LiveDot(label: 'FREE HIT')),
          const SizedBox(height: 6),
          for (final bt in [c['striker'], c['non_striker']])
            if (bt != null) Text('${bt['name']}${bt['player_id'] == c['striker']?['player_id'] ? ' *' : ''}  ${bt['runs']} (${bt['balls']})'),
          if (c['bowler'] != null) Text('🎯 ${c['bowler']['name']}  ${c['bowler']['overs']}-${c['bowler']['maidens']}-${c['bowler']['runs']}-${c['bowler']['wickets']}'),
          const SizedBox(height: 6),
          Wrap(children: [for (final ball in (c['this_over']?['balls'] as List? ?? [])) BallDot('$ball')]),
        ]),
      ),
    );
  }

  Widget _livePad() {
    final c = _c!;
    final ready = c['need_batter'] != true && c['need_bowler'] != true && !_busy;
    Widget runBtn(int r) => FilledButton(
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(60), backgroundColor: r == 4 ? Colors.blue : r == 6 ? Colors.purple : null, textStyle: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900)),
          onPressed: ready ? () => _ball({'runs_bat': r}) : null,
          child: Text('$r'),
        );
    Widget extraBtn(String label, String kind) => OutlinedButton(style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48)), onPressed: ready ? () => _extras(kind) : null, child: Text(label));
    return ListView(padding: const EdgeInsets.all(12), children: [
      _scoreHeader(),
      const SizedBox(height: 8),
      if (c['need_batter'] == true) FilledButton.icon(onPressed: _newBatter, icon: const Icon(Icons.person_add), label: const Text('Select new batter')),
      if (c['need_bowler'] == true) FilledButton.icon(onPressed: _newBowler, icon: const Icon(Icons.sports_baseball), label: const Text('Select bowler for next over')),
      const SizedBox(height: 8),
      GridView.count(
        crossAxisCount: 4,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
        childAspectRatio: 1.4,
        children: [for (final r in [0, 1, 2, 3, 4, 6, 5]) runBtn(r), FilledButton(
          style: FilledButton.styleFrom(backgroundColor: ballRed, minimumSize: const Size.fromHeight(60), textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900)),
          onPressed: ready ? _wicket : null,
          child: const Text('OUT'),
        )],
      ),
      const SizedBox(height: 8),
      Row(children: [
        Expanded(child: extraBtn('Wide', 'wide')), const SizedBox(width: 8),
        Expanded(child: extraBtn('No-ball', 'noball')), const SizedBox(width: 8),
        Expanded(child: extraBtn('Bye', 'bye')), const SizedBox(width: 8),
        Expanded(child: extraBtn('Leg bye', 'legbye')),
      ]),
      const SizedBox(height: 16),
      Wrap(spacing: 8, runSpacing: 8, children: [
        OutlinedButton.icon(onPressed: _busy ? null : _undo, icon: const Icon(Icons.undo), label: const Text('Undo')),
        OutlinedButton.icon(
          onPressed: _busy ? null : () async {
            if (await _confirm('Swap strike?', 'Use this only to correct who is on strike.')) await _call('swap-strike');
          },
          icon: const Icon(Icons.swap_horiz),
          label: const Text('Swap strike'),
        ),
        OutlinedButton.icon(onPressed: _busy || c['bowler'] == null ? null : () => _newBowler(midOver: true), icon: const Icon(Icons.change_circle_outlined), label: const Text('Change bowler')),
        OutlinedButton.icon(onPressed: _busy ? null : _retire, icon: const Icon(Icons.healing), label: const Text('Retire hurt')),
        OutlinedButton.icon(onPressed: _busy ? null : _pause, icon: const Icon(Icons.pause), label: const Text('Pause')),
        OutlinedButton.icon(
          onPressed: _busy ? null : () async {
            if (await _confirm('End this innings?', 'Use this for a declaration or when no batters are left.')) await _call('end-innings', {'reason': 'declared'});
          },
          icon: const Icon(Icons.flag_outlined),
          label: const Text('End innings'),
        ),
      ]),
      const SizedBox(height: 12),
      Text('Editing an older ball, revising overs/target and manual results are on the website scorer panel.', style: Theme.of(context).textTheme.bodySmall),
    ]);
  }
}

class _ExtrasSheet extends StatefulWidget {
  const _ExtrasSheet({required this.kind});
  final String kind;
  @override
  State<_ExtrasSheet> createState() => _ExtrasSheetState();
}

class _ExtrasSheetState extends State<_ExtrasSheet> {
  int _runs = 0;
  String _nbType = 'bat';
  bool _boundary = true;

  @override
  void initState() {
    super.initState();
    if (widget.kind == 'bye' || widget.kind == 'legbye') _runs = 1;
  }

  List<int> get _options => widget.kind == 'noball' && _nbType == 'bat'
      ? [0, 1, 2, 3, 4, 6]
      : widget.kind == 'bye' || widget.kind == 'legbye'
          ? [1, 2, 3, 4]
          : (widget.kind == 'noball' ? [1, 2, 3, 4] : [0, 1, 2, 3, 4]);

  Map<String, dynamic> _payload() {
    final k = widget.kind;
    if (k == 'wide') return {'extra_type': 'wide', 'extra_runs': _runs, 'boundary': _boundary && _runs == 4};
    if (k == 'noball' && _nbType == 'bat') return {'extra_type': 'noball', 'runs_bat': _runs, 'noball_runs_type': 'bat', if (_runs == 4 || _runs == 6) 'boundary': _boundary};
    if (k == 'noball') return {'extra_type': 'noball', 'noball_runs_type': _nbType, 'extra_runs': _runs, 'boundary': _boundary && _runs == 4};
    return {'extra_type': k, 'extra_runs': _runs, 'boundary': _boundary && _runs == 4};
  }

  @override
  Widget build(BuildContext context) {
    const titles = {'wide': 'Wide', 'noball': 'No-ball', 'bye': 'Byes', 'legbye': 'Leg byes'};
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(titles[widget.kind]!, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
          const SizedBox(height: 12),
          if (widget.kind == 'noball')
            SegmentedButton<String>(
              segments: const [ButtonSegment(value: 'bat', label: Text('Off bat')), ButtonSegment(value: 'bye', label: Text('Byes')), ButtonSegment(value: 'legbye', label: Text('Leg byes'))],
              selected: {_nbType},
              onSelectionChanged: (v) => setState(() {
                _nbType = v.first;
                _runs = _options.first;
              }),
            ),
          const SizedBox(height: 12),
          Text(widget.kind == 'wide' ? 'Extra runs run (in addition to the wide)' : 'Runs'),
          const SizedBox(height: 8),
          Wrap(spacing: 8, children: [
            for (final r in _options) ChoiceChip(label: Text('$r', style: const TextStyle(fontSize: 18)), selected: _runs == r, onSelected: (_) => setState(() => _runs = r)),
          ]),
          if (_runs == 4 || _runs == 6)
            CheckboxListTile(contentPadding: EdgeInsets.zero, title: const Text('Reached the boundary'), value: _boundary, onChanged: (v) => setState(() => _boundary = v ?? false)),
          const SizedBox(height: 12),
          FilledButton(onPressed: () => Navigator.pop(context, _payload()), child: const Text('Record')),
        ]),
      ),
    );
  }
}

class _WicketSheet extends StatefulWidget {
  const _WicketSheet({required this.current, required this.fielders, required this.disallowed});
  final Map<String, dynamic> current;
  final List<Map<String, dynamic>> fielders;
  final List<String> disallowed;
  @override
  State<_WicketSheet> createState() => _WicketSheetState();
}

class _WicketSheetState extends State<_WicketSheet> {
  String _kind = 'bowled';
  int? _out;
  int? _fielder;
  int _runs = 0;
  bool _crossed = false;
  String _delivery = 'legal';

  @override
  void initState() {
    super.initState();
    _out = widget.current['striker']?['player_id'] as int?;
  }

  bool get _allowRuns => const ['run_out', 'obstructing_field'].contains(_kind);
  bool get _needsFielder => const ['caught', 'stumped'].contains(_kind);

  Map<String, dynamic> _payload() {
    final p = <String, dynamic>{'wicket': {'kind': _kind, 'player_out': _out, 'fielder': _kind == 'caught_and_bowled' ? null : _fielder}};
    final runs = _allowRuns ? _runs : 0;
    if (_delivery == 'wide') {
      p.addAll({'extra_type': 'wide', 'extra_runs': runs});
    } else if (_delivery == 'noball') {
      p.addAll({'extra_type': 'noball', 'runs_bat': runs});
    } else {
      p['runs_bat'] = runs;
    }
    if (_kind == 'run_out') p['batters_crossed'] = _crossed;
    return p;
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.current;
    final batters = [c['striker'], c['non_striker']].whereType<Map<String, dynamic>>().toList();
    final kinds = dismissalLabels.entries.where((e) => !widget.disallowed.contains(e.key)).toList();
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Text('Wicket', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 6, children: [
              for (final e in kinds)
                ChoiceChip(
                  label: Text(e.value),
                  selected: _kind == e.key,
                  onSelected: (_) => setState(() {
                    _kind = e.key;
                    if (!_allowRuns) _out = c['striker']?['player_id'] as int?;
                  }),
                ),
            ]),
            if (_allowRuns) ...[
              const SizedBox(height: 12),
              const Text('Batter out'),
              Wrap(spacing: 6, children: [
                for (final b in batters) ChoiceChip(label: Text('${b['name']}'), selected: _out == b['player_id'], onSelected: (_) => setState(() => _out = b['player_id'] as int)),
              ]),
              const SizedBox(height: 8),
              const Text('Runs completed before the wicket'),
              Wrap(spacing: 6, children: [for (final r in [0, 1, 2, 3]) ChoiceChip(label: Text('$r'), selected: _runs == r, onSelected: (_) => setState(() => _runs = r))]),
            ],
            if (_kind == 'run_out') CheckboxListTile(contentPadding: EdgeInsets.zero, title: const Text('Batters crossed'), value: _crossed, onChanged: (v) => setState(() => _crossed = v ?? false)),
            if (_needsFielder || _kind == 'run_out') ...[
              const SizedBox(height: 8),
              DropdownButtonFormField<int>(
                initialValue: _fielder,
                decoration: InputDecoration(labelText: _kind == 'stumped' ? 'Wicket-keeper' : (_kind == 'run_out' ? 'Fielder (optional)' : 'Fielder')),
                items: [for (final f in widget.fielders) DropdownMenuItem(value: f['player_id'] as int, child: Text('${f['name']}'))],
                onChanged: (v) => setState(() => _fielder = v),
              ),
            ],
            if (const ['run_out', 'stumped', 'hit_wicket', 'obstructing_field', 'hit_ball_twice'].contains(_kind)) ...[
              const SizedBox(height: 12),
              SegmentedButton<String>(
                segments: const [ButtonSegment(value: 'legal', label: Text('Legal')), ButtonSegment(value: 'wide', label: Text('Wide')), ButtonSegment(value: 'noball', label: Text('No-ball'))],
                selected: {_delivery},
                onSelectionChanged: (v) => setState(() => _delivery = v.first),
              ),
            ],
            const SizedBox(height: 16),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: ballRed),
              onPressed: _needsFielder && _fielder == null ? null : () => Navigator.pop(context, _payload()),
              child: const Text('Record wicket'),
            ),
          ]),
        ),
      ),
    );
  }
}

class _TossCard extends StatefulWidget {
  const _TossCard({required this.snap, required this.call});
  final Map<String, dynamic> snap;
  final Future<bool> Function(String, [Map<String, dynamic>?]) call;
  @override
  State<_TossCard> createState() => _TossCardState();
}

class _TossCardState extends State<_TossCard> {
  int? _winner;
  String _decision = 'bat';
  @override
  Widget build(BuildContext context) {
    final a = widget.snap['team_a'];
    final b = widget.snap['team_b'];
    return ListView(padding: const EdgeInsets.all(16), children: [
      const Text('Toss', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
      const SizedBox(height: 8),
      Wrap(spacing: 8, children: [
        for (final t in [a, b])
          ChoiceChip(label: Text('${t['name']} won'), selected: _winner == t['id'], onSelected: (_) => setState(() => _winner = t['id'] as int)),
      ]),
      const SizedBox(height: 12),
      SegmentedButton<String>(
        segments: const [ButtonSegment(value: 'bat', label: Text('Chose to bat')), ButtonSegment(value: 'bowl', label: Text('Chose to bowl'))],
        selected: {_decision},
        onSelectionChanged: (v) => setState(() => _decision = v.first),
      ),
      const SizedBox(height: 16),
      FilledButton(onPressed: _winner == null ? null : () => widget.call('toss', {'winner': _winner, 'decision': _decision}), child: const Text('Record toss')),
    ]);
  }
}

class _StartInnings extends StatefulWidget {
  const _StartInnings({required this.snap, required this.call});
  final Map<String, dynamic> snap;
  final Future<bool> Function(String, [Map<String, dynamic>?]) call;
  @override
  State<_StartInnings> createState() => _StartInningsState();
}

class _StartInningsState extends State<_StartInnings> {
  int? _s;
  int? _ns;
  int? _b;

  /// Same rule as the server: toss decides innings 1, sides alternate, and a
  /// super over is opened by the side that batted second.
  int _battingTeam() {
    final snap = widget.snap;
    final inns = snap['innings'] as List;
    final a = snap['team_a']['id'] as int;
    final b = snap['team_b']['id'] as int;
    if (inns.isEmpty) {
      final w = snap['toss']['winner'] as int;
      return snap['toss']['decision'] == 'bat' ? w : (w == a ? b : a);
    }
    final last = inns.last;
    return inns.length.isOdd ? last['bowling_team']['id'] as int : last['batting_team']['id'] as int;
  }

  @override
  Widget build(BuildContext context) {
    final snap = widget.snap;
    final bat = _battingTeam();
    final bowl = bat == snap['team_a']['id'] ? snap['team_b']['id'] : snap['team_a']['id'];
    List<Map<String, dynamic>> squad(dynamic id) => ((snap['squads'] as Map)['$id'] as List).cast<Map<String, dynamic>>();
    final batters = squad(bat);
    final bowlers = squad(bowl);
    final team = bat == snap['team_a']['id'] ? snap['team_a'] : snap['team_b'];
    final superOver = (snap['innings'] as List).length >= 2;
    DropdownButtonFormField<int> pick(String label, List<Map<String, dynamic>> players, int? value, ValueChanged<int?> onChanged, {int? exclude}) =>
        DropdownButtonFormField<int>(
          initialValue: value,
          decoration: InputDecoration(labelText: label),
          items: [for (final p in players.where((p) => p['player_id'] != exclude)) DropdownMenuItem(value: p['player_id'] as int, child: Text('${p['name']}'))],
          onChanged: onChanged,
        );
    return ListView(padding: const EdgeInsets.all(16), children: [
      if (snap['result'] == null && (snap['innings'] as List).isNotEmpty) Text('Innings break', style: Theme.of(context).textTheme.bodySmall),
      Text('Start ${superOver ? 'super over' : 'innings ${(snap['innings'] as List).length + 1}'}: ${team['name']} batting', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
      const SizedBox(height: 16),
      pick('Striker', batters, _s, (v) => setState(() => _s = v), exclude: _ns),
      const SizedBox(height: 12),
      pick('Non-striker', batters, _ns, (v) => setState(() => _ns = v), exclude: _s),
      const SizedBox(height: 12),
      pick('Opening bowler', bowlers, _b, (v) => setState(() => _b = v)),
      const SizedBox(height: 16),
      FilledButton(
        onPressed: _s == null || _b == null || (_ns == null && batters.length > 1) ? null : () => widget.call('start-innings', {'striker': _s, 'non_striker': _ns, 'bowler': _b}),
        child: const Text('Start innings'),
      ),
    ]);
  }
}

/// Pick the playing squad for each team from the tournament registration.
class _SquadSetup extends StatefulWidget {
  const _SquadSetup({required this.snap, required this.call});
  final Map<String, dynamic> snap;
  final Future<bool> Function(String, [Map<String, dynamic>?]) call;
  @override
  State<_SquadSetup> createState() => _SquadSetupState();
}

class _SquadSetupState extends State<_SquadSetup> {
  Map<String, dynamic> get _team {
    final s = widget.snap;
    final a = s['team_a'] as Map<String, dynamic>;
    return ((s['squads'] as Map)['${a['id']}'] as List).isEmpty ? a : s['team_b'] as Map<String, dynamic>;
  }

  List<dynamic>? _players;
  final List<int> _selected = [];
  int? _loadedFor;
  String? _error;

  Future<void> _load() async {
    final team = _team;
    _loadedFor = team['id'] as int;
    final api = context.read<ApiClient>();
    try {
      final r = await Future.wait([
        api.get('/tournaments/${widget.snap['tournament']['id']}/registrations/'),
        api.get('/players/', query: {'team': team['id'], 'page_size': 200}),
      ]);
      final reg = (r[0] as List).firstWhere((x) => x['team'] == team['id'], orElse: () => null);
      final registered = ((reg?['players'] as List?) ?? []).cast<int>().toSet();
      var players = ApiClient.list(r[1]);
      if (registered.isNotEmpty) players = players.where((p) => registered.contains(p['id'])).toList();
      final n = (widget.snap['rules'] as Map)['players_per_side'] as int? ?? 11;
      setState(() {
        _players = players;
        _selected
          ..clear()
          ..addAll(players.take(n).map((p) => p['id'] as int));
      });
    } catch (e) {
      setState(() => _error = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loadedFor != _team['id']) {
      _players = null;
      WidgetsBinding.instance.addPostFrameCallback((_) => _load());
    }
    if (_error != null) return ErrorView(_error!, onRetry: _load);
    if (_players == null) return const Center(child: CircularProgressIndicator());
    final n = (widget.snap['rules'] as Map)['players_per_side'] as int? ?? 11;
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(16),
        child: Text('Playing squad: ${_team['name']} (${_selected.length}/$n). Tap in batting order; the first player is captain.', style: const TextStyle(fontWeight: FontWeight.bold)),
      ),
      Expanded(
        child: ListView(children: [
          for (final p in _players!)
            CheckboxListTile(
              value: _selected.contains(p['id']),
              title: Text('${p['full_name']}'),
              subtitle: Text('${p['role']}${_selected.contains(p['id']) ? ' · #${_selected.indexOf(p['id'] as int) + 1}' : ''}'),
              onChanged: (v) => setState(() => v == true ? (_selected.length < n ? _selected.add(p['id'] as int) : null) : _selected.remove(p['id'])),
            ),
        ]),
      ),
      Padding(
        padding: const EdgeInsets.all(16),
        child: FilledButton(
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
          onPressed: _selected.length < 2
              ? null
              : () => widget.call('squad', {
                    'team': _team['id'],
                    'players': [for (final (i, id) in _selected.indexed) {'player': id, 'is_captain': i == 0, 'is_wicket_keeper': false}],
                  }),
          child: const Text('Save squad'),
        ),
      ),
    ]);
  }
}
