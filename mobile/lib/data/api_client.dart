import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({required String baseUrl, http.Client? client})
    : _baseUrl = baseUrl.replaceAll(RegExp(r'/+$'), ''),
      _client = client ?? http.Client();

  final String _baseUrl;
  final http.Client _client;
  String? token;

  Uri _uri(String route) => Uri.parse('$_baseUrl$route');

  Map<String, String> get _headers => {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    if (token != null) 'Authorization': 'Bearer $token',
  };

  Future<Map<String, dynamic>> login(String email, String password) async =>
      _asMap(
        await _send(
          'POST',
          '/auth/login',
          body: {'email': email.trim(), 'password': password},
          authenticated: false,
        ),
      );

  Future<Map<String, dynamic>> register({
    required String invitationToken,
    required String fullName,
    required String password,
  }) async => _asMap(
    await _send(
      'POST',
      '/organizations/invitations/register',
      body: {
        'invitation_token': invitationToken,
        'full_name': fullName,
        'password': password,
      },
      authenticated: false,
    ),
  );

  Future<Map<String, dynamic>> currentUser() async =>
      _asMap(await _send('GET', '/auth/me'));

  Future<void> logout() async => _send('POST', '/auth/logout');

  Future<void> requestPasswordReset(String email) async => _send(
    'POST',
    '/auth/password-reset/request',
    body: {'email': email.trim()},
    authenticated: false,
  );

  Future<Map<String, dynamic>> organization(String organizationId) async =>
      _asMap(await _send('GET', '/organizations/$organizationId'));

  Future<List<Map<String, dynamic>>> vehicles() async =>
      _list(await _send('GET', '/vehicles'));

  Future<List<Map<String, dynamic>>> fuelRecords() async =>
      _list(await _send('GET', '/fuel-records?limit=100'));

  Future<List<Map<String, dynamic>>> alerts() async =>
      _list(await _send('GET', '/alerts?status=OPEN'));

  Future<Map<String, dynamic>> dashboard() async =>
      _asMap(await _send('GET', '/dashboard/summary'));

  Future<Map<String, dynamic>> analytics() async =>
      _asMap(await _send('GET', '/analytics/summary'));

  Future<List<Map<String, dynamic>>> attachments(String recordId) async =>
      _list(await _send('GET', '/fuel-records/$recordId/attachments'));

  Future<Uint8List> downloadAttachment(
    String recordId,
    String attachmentId,
  ) async {
    if (token == null) throw const ApiException('Please sign in again.');
    final response = await _client
        .get(
          _uri('/fuel-records/$recordId/attachments/$attachmentId'),
          headers: _headers,
        )
        .timeout(const Duration(seconds: 30));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        _errorMessage(response),
        statusCode: response.statusCode,
      );
    }
    return response.bodyBytes;
  }

  Future<List<Map<String, dynamic>>> syncFuelRecords(
    List<Map<String, dynamic>> records,
  ) async => _list(
    _asMap(await _send('POST', '/sync/fuel-records', body: records))['results'],
  );

  Future<void> uploadAttachment({
    required String recordId,
    required String kind,
    required List<int> bytes,
    required String filename,
    required String contentType,
  }) async {
    final request =
        http.MultipartRequest(
            'POST',
            _uri('/fuel-records/$recordId/attachments?kind=$kind'),
          )
          ..headers['Authorization'] = 'Bearer ${token ?? ''}'
          ..files.add(
            http.MultipartFile.fromBytes(
              'upload',
              bytes,
              filename: filename,
              contentType: MediaType.parse(contentType),
            ),
          );
    final streamed = await _client
        .send(request)
        .timeout(const Duration(seconds: 30));
    final response = await http.Response.fromStream(streamed);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        _errorMessage(response),
        statusCode: response.statusCode,
      );
    }
  }

  Future<Object?> _send(
    String method,
    String route, {
    Object? body,
    bool authenticated = true,
  }) async {
    if (authenticated && token == null) {
      throw const ApiException('Please sign in again.');
    }
    final uri = _uri(route);
    final headers = _headers;
    late final http.Response response;
    if (method == 'GET') {
      response = await _client
          .get(uri, headers: headers)
          .timeout(const Duration(seconds: 20));
    } else if (method == 'POST') {
      response = await _client
          .post(uri, headers: headers, body: jsonEncode(body))
          .timeout(const Duration(seconds: 20));
    } else {
      throw ArgumentError.value(method, 'method', 'Unsupported HTTP method');
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        _errorMessage(response),
        statusCode: response.statusCode,
      );
    }
    if (response.bodyBytes.isEmpty) return null;
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  String _errorMessage(http.Response response) {
    try {
      final body =
          jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
      final detail = body['detail'];
      if (detail is String) return detail;
      if (detail is List) {
        return detail.map((item) => item['msg'] ?? 'Invalid input').join('\n');
      }
    } catch (_) {
      // Fall back when the server does not return JSON.
    }
    return 'Request failed (${response.statusCode}). Please try again.';
  }

  Map<String, dynamic> _asMap(Object? value) {
    if (value is! Map) {
      throw const FormatException('Expected an object in the API response.');
    }
    return Map<String, dynamic>.from(value);
  }

  List<Map<String, dynamic>> _list(Object? value) {
    if (value is! List) {
      throw const FormatException('Expected a list in the API response.');
    }
    return value.map((item) {
      if (item is! Map) {
        throw const FormatException(
          'Expected an object in the API response list.',
        );
      }
      return Map<String, dynamic>.from(item);
    }).toList();
  }

  void close() => _client.close();
}
