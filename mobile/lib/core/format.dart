import 'package:intl/intl.dart';

String fmtDateTime(String? iso) {
  if (iso == null) return '';
  final d = DateTime.tryParse(iso)?.toLocal();
  return d == null ? '' : DateFormat('d MMM, h:mm a').format(d);
}

String fmtDate(String? iso) {
  if (iso == null) return '';
  final d = DateTime.tryParse(iso)?.toLocal();
  return d == null ? '' : DateFormat('d MMM yyyy').format(d);
}

String num1(dynamic v) => v == null ? '-' : (v is num ? v.toStringAsFixed(2) : '$v');

const dismissalLabels = {
  'bowled': 'Bowled', 'caught': 'Caught', 'caught_and_bowled': 'Caught & bowled', 'lbw': 'LBW',
  'run_out': 'Run out', 'stumped': 'Stumped', 'hit_wicket': 'Hit wicket',
  'obstructing_field': 'Obstructing the field', 'hit_ball_twice': 'Hit the ball twice',
};

const statusLabels = {
  'scheduled': 'Upcoming', 'toss': 'Toss done', 'live': 'LIVE', 'innings_break': 'Innings break',
  'paused': 'Interrupted', 'completed': 'Completed', 'abandoned': 'Abandoned',
};

bool isLiveStatus(String? s) => const ['live', 'innings_break', 'paused'].contains(s);
