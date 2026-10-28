import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/i18n.dart';
import '../widgets/common.dart';
import '../widgets/match_card.dart';

/// Live / upcoming / results lists.
class MatchesScreen extends StatelessWidget {
  const MatchesScreen({super.key, this.initialTab = 0, this.standalone = false});
  final int initialTab;
  final bool standalone;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      initialIndex: initialTab,
      child: Scaffold(
        appBar: AppBar(
          title: Text(context.t(standalone ? 'results' : 'matches')),
          bottom: TabBar(
            labelColor: Theme.of(context).appBarTheme.foregroundColor,
            unselectedLabelColor: Theme.of(context).appBarTheme.foregroundColor?.withValues(alpha: 0.7),
            indicatorColor: Theme.of(context).appBarTheme.foregroundColor,
            tabs: [Tab(text: context.t('live')), Tab(text: context.t('upcoming')), Tab(text: context.t('results'))],
          ),
        ),
        body: const TabBarView(children: [MatchList(state: 'live'), MatchList(state: 'upcoming'), MatchList(state: 'completed')]),
      ),
    );
  }
}

class MatchList extends StatelessWidget {
  const MatchList({super.key, this.state, this.query = const {}});
  final String? state;
  final Map<String, dynamic> query;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return AsyncView<List<dynamic>>(
      load: () async => ApiClient.list(await api.get('/matches/', query: {if (state != null) 'state': state, 'page_size': 100, ...query})),
      builder: (context, items, reload) => RefreshIndicator(
        onRefresh: reload,
        child: items.isEmpty
            ? ListView(children: [EmptyView(context.t(state == 'live' ? 'no_live' : 'nothing'))])
            : ListView.separated(
                padding: const EdgeInsets.all(12),
                itemCount: items.length,
                separatorBuilder: (_, _) => const SizedBox(height: 8),
                itemBuilder: (_, i) => MatchCard(items[i] as Map<String, dynamic>),
              ),
      ),
    );
  }
}
