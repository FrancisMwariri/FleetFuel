import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:medifuel_mobile/data/api_client.dart';

void main() {
  test('posts sync records as a list and reads the per-record results', () async {
    final records = [
      {'client_record_id': 'record-1', 'vehicle_id': 'vehicle-1'},
    ];
    final client = ApiClient(
      baseUrl: 'https://fleet.example/api/v1/',
      client: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/v1/sync/fuel-records');
        expect(jsonDecode(request.body), records);
        expect(request.headers['Authorization'], 'Bearer access-token');
        return http.Response(
          jsonEncode({
            'results': [
              {'client_record_id': 'record-1', 'record_id': 'stored-1', 'status': 'accepted'},
            ],
          }),
          200,
        );
      }),
    )..token = 'access-token';

    expect(
      await client.syncFuelRecords(records),
      [
        {'client_record_id': 'record-1', 'record_id': 'stored-1', 'status': 'accepted'},
      ],
    );
    client.close();
  });

  test('requests password-reset instructions without authentication', () async {
    final client = ApiClient(
      baseUrl: 'https://fleet.example/api/v1',
      client: MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/api/v1/auth/password-reset/request');
        expect(jsonDecode(request.body), {'email': 'driver@example.com'});
        expect(request.headers.containsKey('Authorization'), isFalse);
        return http.Response(
          jsonEncode({'message': 'If the account exists, reset instructions will be sent'}),
          202,
        );
      }),
    );

    await client.requestPasswordReset(' driver@example.com ');
    client.close();
  });

  test('loads the current organization for its configured currency', () async {
    final client = ApiClient(
      baseUrl: 'https://fleet.example/api/v1',
      client: MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/api/v1/organizations/org-1');
        expect(request.headers['Authorization'], 'Bearer access-token');
        return http.Response(
          jsonEncode({'id': 'org-1', 'default_currency': 'KES'}),
          200,
        );
      }),
    )..token = 'access-token';

    expect(await client.organization('org-1'), {
      'id': 'org-1',
      'default_currency': 'KES',
    });
    client.close();
  });

  test('lists attachment metadata and downloads its image with authorization', () async {
    final client = ApiClient(
      baseUrl: 'https://fleet.example/api/v1',
      client: MockClient((request) async {
        expect(request.headers['Authorization'], 'Bearer access-token');
        if (request.url.path.endsWith('/attachments')) {
          return http.Response(
            jsonEncode([
              {
                'id': 'attachment-1',
                'kind': 'RECEIPT',
                'content_type': 'image/png',
                'size_bytes': 3,
                'created_at': '2026-10-22T06:00:00Z',
              },
            ]),
            200,
          );
        }
        expect(request.url.path, '/api/v1/fuel-records/record-1/attachments/attachment-1');
        return http.Response.bytes([1, 2, 3], 200);
      }),
    )..token = 'access-token';

    final attachments = await client.attachments('record-1');
    expect(attachments.single['kind'], 'RECEIPT');
    expect(await client.downloadAttachment('record-1', 'attachment-1'), [1, 2, 3]);
    client.close();
  });
}
