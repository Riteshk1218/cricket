import 'dart:async';
import 'dart:convert';
import 'dart:io' show Platform, SocketException;

import 'package:http/http.dart' as http;

import 'app_state.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.status, this.code, this.data});
  final String message;
  final int? status;
  final String? code;
  final dynamic data;

  bool get isConflict => status == 409;

  @override
  String toString() => message;
}

/// Small REST client for the Django API with JWT refresh and friendly errors.
class ApiClient {
  ApiClient(this.state);
  final AppState state;
  // Long enough for the free hosted server to wake up from sleep (about a minute).
  static const _timeout = Duration(seconds: 75);

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final q = query?.map((k, v) => MapEntry(k, '$v'))?..removeWhere((k, v) => v == 'null');
    return Uri.parse('${state.apiUrl}$path').replace(queryParameters: q == null || q.isEmpty ? null : q);
  }

  Map<String, String> _headers() => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (state.accessToken != null) 'Authorization': 'Bearer ${state.accessToken}',
      };

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) => _send('GET', path, query: query);
  Future<dynamic> post(String path, [Map<String, dynamic>? body]) => _send('POST', path, body: body);
  Future<dynamic> patch(String path, Map<String, dynamic> body) => _send('PATCH', path, body: body);
  Future<dynamic> delete(String path) => _send('DELETE', path);

  /// Unwraps paginated list responses.
  static List<dynamic> list(dynamic data) => data is List ? data : (data?['results'] as List? ?? []);

  Future<dynamic> _send(String method, String path, {Map<String, dynamic>? query, Map<String, dynamic>? body, bool retry = true}) async {
    http.Response res;
    try {
      final req = http.Request(method, _uri(path, query))..headers.addAll(_headers());
      if (body != null) req.body = jsonEncode(body);
      res = await http.Response.fromStream(await req.send().timeout(_timeout));
    } on TimeoutException {
      throw ApiException('The server did not respond. It may be waking up: wait a minute and tap Retry. Also check the server address in Settings.');
    } on SocketException {
      throw ApiException('Cannot reach ${state.serverUrl}. Start the backend with "runserver 0.0.0.0:8000" and check the IP address.');
    } on http.ClientException catch (e) {
      throw ApiException('Network error: ${e.message}');
    }
    if (res.statusCode == 401 && retry && state.refreshToken != null && !path.startsWith('/auth/')) {
      if (await _refresh()) return _send(method, path, query: query, body: body, retry: false);
    }
    final text = utf8.decode(res.bodyBytes);
    final data = text.isEmpty ? null : _tryJson(text);
    if (res.statusCode >= 400) {
      throw ApiException(_message(data, res.statusCode), status: res.statusCode, code: data is Map ? data['code'] as String? : null, data: data);
    }
    return data;
  }

  dynamic _tryJson(String text) {
    try {
      return jsonDecode(text);
    } catch (_) {
      return text;
    }
  }

  String _message(dynamic data, int status) {
    if (data is Map) {
      if (data['detail'] != null) return '${data['detail']}';
      return data.entries.map((e) => '${e.key}: ${e.value is List ? (e.value as List).join(' ') : e.value}').join('\n');
    }
    if (status == 401) return 'Please log in again.';
    return 'Request failed ($status)';
  }

  Future<bool> _refresh() async {
    try {
      final res = await http
          .post(_uri('/auth/refresh/'), headers: {'Content-Type': 'application/json'}, body: jsonEncode({'refresh': state.refreshToken}))
          .timeout(_timeout);
      if (res.statusCode != 200) {
        await state.setSession(access: null);
        return false;
      }
      final d = jsonDecode(res.body) as Map<String, dynamic>;
      await state.setSession(access: d['access'] as String, refresh: d['refresh'] as String?);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> login(String username, String password) async {
    final d = await post('/auth/login/', {'username': username, 'password': password}) as Map<String, dynamic>;
    await state.setSession(access: d['access'] as String, refresh: d['refresh'] as String, userData: d['user'] as Map<String, dynamic>);
    return d['user'] as Map<String, dynamic>;
  }

  Future<void> register(String username, String email, String password, String name) async {
    await post('/auth/register/', {'username': username, 'email': email, 'password': password, 'display_name': name, 'preferred_language': state.language});
    await login(username, password);
  }

  Future<void> logout() async {
    try {
      if (state.refreshToken != null) await post('/auth/logout/', {'refresh': state.refreshToken});
    } catch (_) {}
    await state.setSession(access: null);
  }

  String get clientType {
    try {
      return Platform.isIOS ? 'ios' : 'android';
    } catch (_) {
      return 'android';
    }
  }

  /// Anonymous screen-view beacon (no personal data; the id is random and hashed daily on the server).
  void track(String screen, {int? matchId}) {
    post('/analytics/track/', {'path': 'app:$screen', 'visitor_id': state.visitorId, 'client': clientType, 'match': matchId}).catchError((_) => null);
  }

  Future<bool> ping() async {
    try {
      await get('/health/');
      return true;
    } catch (_) {
      return false;
    }
  }
}
