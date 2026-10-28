import 'package:flutter/material.dart';

import '../core/i18n.dart';
import '../core/theme.dart';

class TeamBadge extends StatelessWidget {
  const TeamBadge(this.team, {super.key, this.size = 36});
  final Map<String, dynamic>? team;
  final double size;

  @override
  Widget build(BuildContext context) {
    final color = hexColor(team?['primary_color'] as String?);
    final label = (team?['short_name'] as String?)?.isNotEmpty == true ? team!['short_name'] as String : (team?['name'] as String? ?? '?');
    return CircleAvatar(
      radius: size / 2,
      backgroundColor: color,
      child: Text(label.length > 3 ? label.substring(0, 3) : label,
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: size * 0.3)),
    );
  }
}

class LiveDot extends StatelessWidget {
  const LiveDot({super.key, this.label = 'LIVE'});
  final String label;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(color: ballRed, borderRadius: BorderRadius.circular(6)),
        child: Text(label, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.bold)),
      );
}

class ErrorView extends StatelessWidget {
  const ErrorView(this.message, {super.key, this.onRetry});
  final String message;
  final VoidCallback? onRetry;
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.wifi_off, size: 48, color: Colors.grey),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              FilledButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh), label: Text(context.t('retry'))),
            ],
          ]),
        ),
      );
}

class EmptyView extends StatelessWidget {
  const EmptyView(this.message, {super.key, this.icon = Icons.sports_cricket});
  final String message;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(icon, size: 48, color: Colors.grey),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey)),
          ]),
        ),
      );
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key, this.trailing});
  final String text;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
        child: Row(children: [
          Expanded(child: Text(text, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold))),
          ?trailing,
        ]),
      );
}

/// One delivery in an over strip: 4/6/W coloured like the website.
class BallDot extends StatelessWidget {
  const BallDot(this.label, {super.key, this.size = 30});
  final String label;
  final double size;
  @override
  Widget build(BuildContext context) {
    Color bg = Theme.of(context).colorScheme.surfaceContainerHighest;
    Color fg = Theme.of(context).colorScheme.onSurface;
    if (label.contains('W')) {
      bg = ballRed;
      fg = Colors.white;
    } else if (label == '6') {
      bg = Colors.purple;
      fg = Colors.white;
    } else if (label == '4') {
      bg = Colors.blue;
      fg = Colors.white;
    } else if (RegExp(r'wd|nb|b|lb|p').hasMatch(label)) {
      bg = gold.withValues(alpha: 0.35);
    }
    return Container(
      width: label.length > 2 ? null : size,
      height: size,
      padding: EdgeInsets.symmetric(horizontal: label.length > 2 ? 6 : 0),
      margin: const EdgeInsets.only(right: 4),
      alignment: Alignment.center,
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(size / 2)),
      child: Text(label, style: TextStyle(color: fg, fontWeight: FontWeight.bold, fontSize: 12)),
    );
  }
}

/// Simple loader for a future with error + retry handling.
class AsyncView<T> extends StatefulWidget {
  const AsyncView({super.key, required this.load, required this.builder});
  final Future<T> Function() load;
  final Widget Function(BuildContext context, T data, Future<void> Function() reload) builder;

  @override
  State<AsyncView<T>> createState() => _AsyncViewState<T>();
}

class _AsyncViewState<T> extends State<AsyncView<T>> {
  T? _data;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    setState(() {
      _loading = _data == null;
      _error = null;
    });
    try {
      final d = await widget.load();
      if (mounted) setState(() => _data = d);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null && _data == null) return ErrorView(_error!, onRetry: _reload);
    return widget.builder(context, _data as T, _reload);
  }
}
