import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/app_state.dart';
import '../core/i18n.dart';
import '../core/live_socket.dart';
import '../widgets/common.dart';
import '../widgets/match_card.dart';
import 'settings_screen.dart';

/// Dashboard: live matches (updated over the live_scores WebSocket), upcoming fixtures and results.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Map<String, dynamic>> _live = [];
  List<Map<String, dynamic>> _upcoming = [];
  List<Map<String, dynamic>> _results = [];
  String? _error;
  bool _loading = true;
  LiveSocket? _socket;
  SocketStatus _status = SocketStatus.connecting;
  String? _server;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final server = context.watch<AppState>().serverUrl;
    if (server != _server) {
      _server = server;
      _load();
      _connect();
    }
  }

  void _connect() {
    _socket?.close();
    final s = context.read<AppState>();
    _socket = LiveSocket('${s.wsUrl}/ws/live/?client=${context.read<ApiClient>().clientType}', onMessage: _onMessage, onStatus: (st) {
      if (mounted) setState(() => _status = st);
    })
      ..connect();
  }

  void _onMessage(Map<String, dynamic> msg) {
    if (msg['type'] != 'summary' || !mounted) return;
    final m = Map<String, dynamic>.from(msg['summary'] as Map);
    setState(() {
      final i = _live.indexWhere((x) => x['id'] == m['id']);
      final isLive = const ['live', 'innings_break', 'paused'].contains(m['status']);
      if (i >= 0 && isLive) {
        if ((m['version'] as int? ?? 0) >= (_live[i]['version'] as int? ?? 0)) _live[i] = m;
      } else if (i >= 0) {
        _live.removeAt(i);
        _results.insert(0, m);
      } else if (isLive) {
        _live.add(m);
        _upcoming.removeWhere((x) => x['id'] == m['id']);
      }
    });
  }

  Future<void> _load() async {
    final api = context.read<ApiClient>();
    setState(() {
      _loading = _live.isEmpty && _upcoming.isEmpty;
      _error = null;
    });
    try {
      final r = await Future.wait([
        api.get('/matches/', query: {'state': 'live', 'page_size': 12}),
        api.get('/matches/', query: {'state': 'upcoming', 'page_size': 6}),
        api.get('/matches/', query: {'state': 'completed', 'page_size': 6}),
      ]);
      api.track('home');
      if (!mounted) return;
      setState(() {
        _live = ApiClient.list(r[0]).cast<Map<String, dynamic>>();
        _upcoming = ApiClient.list(r[1]).cast<Map<String, dynamic>>();
        _results = ApiClient.list(r[2]).cast<Map<String, dynamic>>();
      });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _socket?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(context.t('app'), style: const TextStyle(fontWeight: FontWeight.w900)),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Icon(Icons.circle, size: 10, color: _status == SocketStatus.open ? Colors.lightGreenAccent : Colors.orange),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null && _live.isEmpty
              ? ErrorView(_error!, onRetry: () {
                  _load();
                  _connect();
                })
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.only(bottom: 24), children: [
                    if (_error != null)
                      MaterialBanner(content: Text(_error!), actions: [
                        TextButton(onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen())), child: Text(context.t('settings'))),
                      ]),
                    SectionTitle(context.t('live_now'), trailing: _status == SocketStatus.open ? null : Text(context.t('reconnecting'), style: const TextStyle(color: Colors.orange, fontSize: 12))),
                    if (_live.isEmpty) EmptyView(context.t('no_live')),
                    ..._live.map(_pad),
                    if (_upcoming.isNotEmpty) SectionTitle(context.t('upcoming')),
                    ..._upcoming.map(_pad),
                    if (_results.isNotEmpty) SectionTitle(context.t('results')),
                    ..._results.map(_pad),
                  ]),
                ),
    );
  }

  Widget _pad(Map<String, dynamic> m) => Padding(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4), child: MatchCard(m));
}
