import 'package:flutter/material.dart';

import '../core/theme.dart';

/// Full-screen FOUR / SIX / WICKET burst. It ignores touches so it never blocks the UI.
class CelebrationOverlay extends StatefulWidget {
  const CelebrationOverlay({super.key, required this.kind, required this.label, required this.onDone});
  final String kind;
  final String label;
  final VoidCallback onDone;

  @override
  State<CelebrationOverlay> createState() => _CelebrationOverlayState();
}

class _CelebrationOverlayState extends State<CelebrationOverlay> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1800))
    ..forward().whenComplete(widget.onDone);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = switch (widget.kind) { 'six' => Colors.purple, 'wicket' => ballRed, _ => Colors.blue };
    return IgnorePointer(
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, _) {
          final t = _c.value;
          final scale = Curves.elasticOut.transform((t * 2).clamp(0.0, 1.0));
          final opacity = t < 0.75 ? 1.0 : (1 - (t - 0.75) / 0.25);
          return Opacity(
            opacity: opacity.clamp(0.0, 1.0),
            child: Container(
              color: color.withValues(alpha: 0.18),
              alignment: Alignment.center,
              child: Transform.scale(
                scale: 0.4 + scale * 0.6,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 18),
                  decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(24), boxShadow: const [BoxShadow(blurRadius: 24, color: Colors.black26)]),
                  child: Text(widget.label, style: const TextStyle(color: Colors.white, fontSize: 44, fontWeight: FontWeight.w900, letterSpacing: 2)),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
