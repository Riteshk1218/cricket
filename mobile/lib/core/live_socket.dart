import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

enum SocketStatus { connecting, open, reconnecting, closed }

/// WebSocket feed with automatic reconnect (exponential backoff) and heartbeats.
class LiveSocket {
  LiveSocket(this.url, {required this.onMessage, this.onStatus});

  final String url;
  final void Function(Map<String, dynamic> message) onMessage;
  final void Function(SocketStatus status)? onStatus;

  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  Timer? _retryTimer;
  Timer? _pingTimer;
  int _attempt = 0;
  bool _closed = false;

  void connect() {
    _closed = false;
    _open();
  }

  void _open() {
    onStatus?.call(_attempt == 0 ? SocketStatus.connecting : SocketStatus.reconnecting);
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
    } catch (_) {
      _scheduleRetry();
      return;
    }
    _channel!.ready.then((_) {
      _attempt = 0;
      onStatus?.call(SocketStatus.open);
      _pingTimer?.cancel();
      _pingTimer = Timer.periodic(const Duration(seconds: 25), (_) => send({'type': 'ping'}));
    }).catchError((_) {});
    _sub = _channel!.stream.listen(
      (data) {
        try {
          onMessage(jsonDecode(data as String) as Map<String, dynamic>);
        } catch (_) {}
      },
      onDone: _scheduleRetry,
      onError: (_) => _scheduleRetry(),
      cancelOnError: true,
    );
  }

  void _scheduleRetry() {
    _pingTimer?.cancel();
    _sub?.cancel();
    if (_closed) return;
    onStatus?.call(SocketStatus.reconnecting);
    _attempt++;
    final delay = Duration(milliseconds: (500 * (1 << _attempt.clamp(0, 5))).clamp(500, 15000));
    _retryTimer?.cancel();
    _retryTimer = Timer(delay, _open);
  }

  void send(Map<String, dynamic> msg) {
    try {
      _channel?.sink.add(jsonEncode(msg));
    } catch (_) {}
  }

  void resync() => send({'type': 'resync'});

  void close() {
    _closed = true;
    _retryTimer?.cancel();
    _pingTimer?.cancel();
    _sub?.cancel();
    _channel?.sink.close();
    onStatus?.call(SocketStatus.closed);
  }
}
